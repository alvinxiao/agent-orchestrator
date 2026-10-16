# Task contracts, version 1

Run `orchestrator validate examples/tasks/example.yaml`. Validation returns a JSON
object with `valid: true` and `task_ids`, or `valid: false` and an `errors` list whose
items have `code`, `path`, and `message`. Exit status is 0 for valid and 2 for invalid.
The first error is reported deterministically. Syntax/read errors use `$`; field
errors identify the zero-based task index and field. Validation reads only the
specified file; it never executes acceptance commands, enables an executor, fetches
repositories, or creates state.

Use the example as the schema. All fields, including nested fields, are required;
unknown fields are rejected. Input is one mapping or a list of mappings containing
a complete task set. Files must be UTF-8 YAML, at most 1 MiB. Duplicate mapping keys,
non-string keys, aliases, and custom object tags are rejected. Quote text that YAML
would otherwise interpret as a boolean or number.

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1`; booleans rejected |
| `id` | Uppercase prefix and at least three digits, e.g. `ORCH-002` |
| `title` | Nonempty text |
| `repository` | Repository name or `owner/name`; not a URL or filesystem path |
| `depends_on` | Unique task IDs; empty allowed |
| `scope.allowed_paths` | Nonempty list of relative POSIX paths/globs; no absolute paths, traversal, backslashes, drive prefixes, or empty components |
| `requirements` | Nonempty list of nonempty strings |
| `acceptance.commands` | Nonempty list of command strings with valid shell-style quoting; no shell operators, expansion, newlines, or environment assignments before executable |
| `acceptance.required_tests` | Nonempty list of named behavioral checks |
| `execution.executor` | `mock` or `codex`; declaration only, neither runs |
| `execution.max_attempts` | Integer 1–3, including the initial attempt |
| `execution.timeout_minutes` | Positive integer, not a boolean or fractional number |
| `permissions.network` | `disabled` or `restricted` |
| Other permission fields | Explicit boolean false for production access, secrets access, merge, and deploy |
| `risk_level` | `low`, `medium`, or `high` |

Each list rejects duplicates. A task set rejects duplicate IDs, unknown dependencies,
self-dependencies, and cycles. Output retains input task order; validation does not
schedule tasks. To validate a dependent task, supply its prerequisites in the same
list. Standalone files cannot resolve dependencies against an external registry yet.

Commands retain the specification's string representation. Syntax validation is
conservative and rejects shell metacharacters even inside quotes. It is not an
execution sandbox or an executable allowlist: a syntactically valid command can
still be dangerous. A future runner must independently enforce execution policy,
workspace boundaries, approved executables, and timeouts. Path validation is lexical;
resolving symlinks safely belongs to workspace allocation and execution.

The schema adds explicit `schema_version: 1` to the engineering specification's
example, and uses `disabled` for offline mock work. All elevated permissions remain
rejected until policy/approval handling exists. No permission grant or billing
integration is introduced by this implementation. Scheduler, persistence, retries,
and provider adapters remain separate tickets.
