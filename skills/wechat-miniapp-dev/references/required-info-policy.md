# Required Info Policy

Classify missing information by the current task, not by a fixed checklist.

## Classes

- `blocking`: The current task cannot safely continue.
- `warning`: The task can continue only after user confirmation.
- `optional`: The task can continue without confirmation.

Record blocking and warning items in `docs/ai/miniapp/required-info.md`. Record warning confirmations and their risks in `current-plan.md`.

## Examples

| Missing Information | Local Code/Edit | Trial Upload | Review/Release | Remote Repo/Push |
|---|---|---|---|---|
| AppID | warning | blocking | blocking | optional |
| Cloud environment | warning for cloud features | blocking for cloud upload/deploy | blocking when used | optional |
| WeChat DevTools | warning | blocking | blocking | optional |
| Git authorization | optional | optional | optional | blocking |
| Payment config | optional for static work, blocking for payment integration | blocking for payment flow upload | blocking for payment release | optional |
| API docs | warning for integration work | warning | warning | optional |
| Secrets or credentials | blocking when execution needs them | blocking when execution needs them | blocking when execution needs them | blocking when execution needs them |

Do not write plaintext secrets into project files.

