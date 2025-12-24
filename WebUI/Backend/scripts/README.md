# Scripts Directory

This directory contains all automation scripts organized by functionality.

## Structure

```
scripts/
├── bulk/              # Bulk device operations
│   ├── BulkAdd-WUGv14.py
│   ├── BulkUpdate-WUGv14.py
│   ├── BulkDelete-WUGv14.py
│   └── db_config.py   # Database configuration
├── routers/           # Router command execution
│   ├── Simple_Config.py
│   └── Interactive_Commands.py
├── backup/            # Configuration backup scripts
│   ├── Get Running Config.py
│   ├── Get Startup Conifg.py
│   ├── backup_config.py
│   └── routers.txt    # Router list for backups
└── reporting/         # Report generation
    ├── ReportExcel.py
    ├── report_config.py
    └── report_schedule.xlsx
```

## Migration Notes

Scripts have been moved from:

- `Bulk Changes/Code/` → `scripts/bulk/`
- `Many Routers Config/` → `scripts/routers/`
- `Config Backup/` → `scripts/backup/`
- `Reporting/` → `scripts/reporting/`

All paths in `main.py` have been updated to use the new structure.
