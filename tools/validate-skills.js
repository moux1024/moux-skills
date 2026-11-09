#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const skillsDir = path.join(root, "skills");
const registryPath = path.join(root, "registry.json");

function walk(dir, results = []) {
  if (!fs.existsSync(dir)) {
    return results;
  }

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath, results);
    } else if (entry.isFile() && entry.name === "SKILL.md") {
      results.push(fullPath);
    }
  }

  return results;
}

function looksLikeUnquotedColon(value) {
  const v = value.trim();
  if (!v) return false;
  // Quoted scalars and block scalars are legal; a real YAML parser owns those.
  if (/^["']/.test(v) || /^[|>][+-]?\d*$/.test(v)) return false;
  // In a plain scalar, ": " opens a nested mapping. Real parsers reject it with
  // "mapping values are not allowed in this context". A line-based regex parser
  // silently accepts it, which is how a 998-char description saying
  // "deliverables: ..." shipped a SKILL.md that no YAML parser could read.
  return v.includes(": ");
}

function parseFrontmatter(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) {
    return null;
  }

  const metadata = {};
  for (const line of match[1].split("\n")) {
    const pair = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (pair) {
      if (looksLikeUnquotedColon(pair[2])) {
        fail(`${path.relative(root, filePath)}: frontmatter "${pair[1]}" has an unquoted ": " — `
          + `YAML parsers reject this. Wrap the value in quotes or use a block scalar (>-).`);
      }
      metadata[pair[1]] = pair[2].replace(/^["']|["']$/g, "").trim();
    }
  }

  return metadata;
}

function fail(message) {
  console.error(`ERROR: ${message}`);
  process.exitCode = 1;
}

const skillFiles = walk(skillsDir);
const skillPaths = new Set();
const names = new Set();

if (skillFiles.length === 0) {
  fail("No skills found. Add at least one skills/<id>/SKILL.md file.");
}

for (const filePath of skillFiles) {
  const relativeSkillPath = path.relative(root, path.dirname(filePath));
  const metadata = parseFrontmatter(filePath);
  skillPaths.add(relativeSkillPath);

  if (!metadata) {
    fail(`${relativeSkillPath}/SKILL.md is missing YAML frontmatter.`);
    continue;
  }

  if (!metadata.name) {
    fail(`${relativeSkillPath}/SKILL.md is missing required metadata: name.`);
  }

  if (!metadata.description) {
    fail(`${relativeSkillPath}/SKILL.md is missing required metadata: description.`);
  }

  if (metadata.name) {
    if (names.has(metadata.name)) {
      fail(`Duplicate skill name: ${metadata.name}.`);
    }
    names.add(metadata.name);
  }
}

if (fs.existsSync(registryPath)) {
  const registry = JSON.parse(fs.readFileSync(registryPath, "utf8"));
  if (!Array.isArray(registry)) {
    fail("registry.json must contain an array.");
  } else {
    for (const item of registry) {
      if (!item.id || !item.name || !item.description || !item.repo || !item.path) {
        fail("Every registry item must include id, name, description, repo, and path.");
        continue;
      }

      if (!skillPaths.has(item.path)) {
        fail(`registry.json points at missing skill path: ${item.path}.`);
      }
    }
  }
}

if (!process.exitCode) {
  console.log(`Validated ${skillFiles.length} skill(s).`);
}

