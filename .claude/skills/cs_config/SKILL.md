---
name: cs_config
description: View or update Claudshi plugin settings (risk limits, edge thresholds, categories). Use when managing configuration.
disable-model-invocation: true
argument-hint: "[key value | reset]"
allowed-tools: Read Write Bash
---

# /cs_config — View or Update Plugin Settings

## Usage

```
/cs_config                      # Show all current settings
/cs_config <key> <value>        # Update a single setting
/cs_config reset                # Restore all defaults
```

## Instructions

The user's arguments: $ARGUMENTS

When the user invokes `/cs_config`, follow these steps based on the arguments provided.

### No Arguments — Show Settings

1. Run the following Python snippet to load the current configuration:

```python
import sys; sys.path.insert(0, "lib")
from memory import load_config, DEFAULT_CONFIG
config = load_config()
```

2. Display a markdown table with three columns: **Setting**, **Current Value**, **Default**. For each supported setting, show the current value and the default side by side so the user can see what has been customized.

Supported settings and their defaults:

| Setting | Default |
|---------|---------|
| `max_single_bet_usd` | 50 |
| `max_position_usd` | 200 |
| `max_portfolio_exposure_usd` | 1000 |
| `min_edge_pct` | 10 |
| `confidence_threshold` | 0.6 |
| `monitor_interval_hours` | 12 |
| `categories` | `[politics, geopolitics, elections, legislation]` |

3. Mark any value that differs from its default with a `*` indicator so customizations are easy to spot.

### `<key> <value>` — Update a Setting

1. Validate that `<key>` is one of the supported settings listed above. If not, show an error listing the valid keys.
2. Parse `<value>` to the appropriate type:
   - Integer keys: `max_single_bet_usd`, `max_position_usd`, `max_portfolio_exposure_usd`, `min_edge_pct`, `monitor_interval_hours`
   - Float keys: `confidence_threshold`
   - List keys: `categories` (accept comma-separated values, e.g. `politics,elections`)
3. Load the current config, update the key, and save:

```python
import sys; sys.path.insert(0, "lib")
from memory import load_config, save_config
config = load_config()
config["<key>"] = <parsed_value>
save_config(config)
```

4. Display the updated settings table (same format as "Show Settings") so the user can confirm the change.

### `reset` — Restore Defaults

1. Save the default configuration:

```python
import sys; sys.path.insert(0, "lib")
from memory import save_config, DEFAULT_CONFIG
save_config(dict(DEFAULT_CONFIG))
```

2. Display the settings table showing all values restored to defaults.
3. Confirm to the user: "All settings restored to defaults."

## Validation Rules

- `max_single_bet_usd` must be a positive integer.
- `max_position_usd` must be a positive integer and >= `max_single_bet_usd`.
- `max_portfolio_exposure_usd` must be a positive integer and >= `max_position_usd`.
- `min_edge_pct` must be an integer between 1 and 50.
- `confidence_threshold` must be a float between 0.0 and 1.0.
- `monitor_interval_hours` must be a positive integer.
- `categories` must be a non-empty list of strings.

If validation fails, show the error and do not save.

## Output Format

```
## Claudshi Configuration

| Setting                       | Current Value                                  | Default                                        |
|-------------------------------|------------------------------------------------|------------------------------------------------|
| max_single_bet_usd            | 100 *                                          | 50                                             |
| max_position_usd              | 200                                            | 200                                            |
| max_portfolio_exposure_usd    | 1000                                           | 1000                                           |
| min_edge_pct                  | 10                                             | 10                                             |
| confidence_threshold          | 0.6                                            | 0.6                                            |
| monitor_interval_hours        | 12                                             | 12                                             |
| categories                    | politics, geopolitics, elections, legislation   | politics, geopolitics, elections, legislation   |

`*` = customized (differs from default)
```
