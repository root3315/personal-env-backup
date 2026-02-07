# personal-env-backup

Backup and restore dotfiles and environment configurations for personal machines.

## Features

- **Auto-discovery** of common dotfiles and config directories (`.bashrc`, `.zshrc`, `.vimrc`, `.gitconfig`, `.ssh/config`, `.config/*`, etc.)
- **Compressed archives** — backups are stored as `.tar.gz` files
- **Manifest generation** — each backup includes a JSON manifest with checksums, sizes, and metadata
- **Integrity verification** — verify archive contents are not corrupt
- **Selective restore** — interactive prompts before overwriting, with a `--force` option
- **Cleanup** — keep only the N most recent backups
- **Dry-run mode** — preview what would be backed up without writing anything

## Requirements

- Python 3.6+
- No third-party dependencies (uses only standard library)

## Quick Start

```bash
# Clone or download the script
chmod +x personal_env_backup.py

# See what would be backed up
python3 personal_env_backup.py discover

# Create a backup
python3 personal_env_backup.py backup

# Dry run first
python3 personal_env_backup.py backup --dry-run

# List all backups
python3 personal_env_backup.py list

# Restore from a backup
python3 personal_env_backup.py restore ~/.personal-env-backups/personal-env-backup_20260414_103000.tar.gz

# Force restore (overwrite without prompting)
python3 personal_env_backup.py restore ~/.personal-env-backups/personal-env-backup_20260414_103000.tar.gz --force

# Verify archive integrity
python3 personal_env_backup.py verify ~/.personal-env-backups/personal-env-backup_20260414_103000.tar.gz

# Keep only the 3 most recent backups
python3 personal_env_backup.py cleanup --keep 3
```

## Commands

| Command      | Description                                    |
|-------------|------------------------------------------------|
| `discover`   | Show all dotfiles/configs that would be backed up |
| `backup`     | Create a new compressed backup                 |
| `list`       | List existing backups with size and date       |
| `restore`    | Restore dotfiles from a backup archive         |
| `verify`     | Check archive integrity                        |
| `cleanup`    | Remove old backups, keeping the latest N       |

## Options

### backup

| Flag         | Description                           |
|-------------|---------------------------------------|
| `-o`, `--output` | Custom backup output directory   |
| `-l`, `--label`  | Custom label for the backup name  |
| `--dry-run`      | Preview files without creating archive |

### restore

| Flag           | Description                          |
|---------------|--------------------------------------|
| `-t`, `--target` | Restore to a different directory   |
| `-f`, `--force`  | Overwrite existing files silently  |

### cleanup

| Flag            | Description                           |
|----------------|---------------------------------------|
| `-k`, `--keep`  | Number of recent backups to keep (default: 5) |
| `-o`, `--output`| Backup directory to clean             |

## Customization

Edit the `COMMON_DOTFILES` and `CONFIG_DIRS` lists at the top of `personal_env_backup.py` to include or exclude specific paths.

## Backup Storage

By default, backups are stored in `~/.personal-env-backups/`. Use `-o` / `--output` on any command to specify a different location.

## License

MIT
