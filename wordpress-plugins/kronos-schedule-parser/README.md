# Kronos Schedule Parser

A WordPress plugin that parses Kronos daily grid PDF reports and displays employee schedules with automatically calculated tea breaks and lunch breaks in a visual table format.

## Features

- **PDF Parsing**: Upload and parse Kronos daily grid PDF reports
- **Visual Schedule Table**: 
  - Date displayed at top left
  - 15-minute interval columns starting at 6:00 AM
  - Employee names with job titles displayed below (greyed out styling)
  - Shifts shown as greyed-out cells
- **Automatic Break Calculation**:
  - **Tea Break (T)**: 15 minutes, 2 hours into shift for shifts 4+ hours
  - **Lunch Break (X)**: Marked in the middle of shifts 6+ hours
  - **Second Tea Break (T)**: 15 minutes, 2 hours before end for shifts 7.5+ hours
- **Shortcode Support**: Display schedules on any page or post
- **Responsive Design**: Works on desktop and mobile devices

## Installation

1. Upload the `kronos-schedule-parser` folder to `/wp-content/plugins/`
2. Activate the plugin through the 'Plugins' menu in WordPress
3. Access the plugin via 'Kronos Schedule' in the admin menu

## Usage

### Admin Interface

1. Navigate to **Kronos Schedule** in the WordPress admin menu
2. Upload a Kronos daily grid PDF report using the upload form
3. The schedule will be parsed and displayed automatically
4. Click "Load Sample Data" to see an example schedule

### Shortcode

Display the parsed schedule on any page or post:

```
[kronos_schedule]
```

## Break Rules

The plugin automatically calculates breaks based on shift duration:

| Shift Duration | Breaks Applied |
|---------------|----------------|
| < 4 hours | No breaks |
| 4-5.9 hours | 1 tea break (15 min, 2 hours into shift) |
| 6-7.4 hours | 1 tea break + 1 lunch break |
| 7.5+ hours | 2 tea breaks + 1 lunch break |

## Table Layout

- **Date**: Displayed prominently at the top left
- **Columns**: Each column represents 15 minutes
- **Start Time**: 6:00 AM
- **Employee Row**: 
  - Name in bold
  - Job title below in grey/italic
- **Shift Cells**: Greyed out to indicate working hours
- **Break Markers**:
  - **T** = Tea break (green)
  - **X** = Lunch break (yellow/orange)

## PDF Requirements

For best results, the Kronos PDF should contain:
- Employee names
- Job titles/positions
- Shift start and end times

Supported formats:
- Standard Kronos daily grid reports
- Time format: 24-hour (08:00) or 12-hour (8:00 AM)

## Technical Notes

- Requires PHP 7.2 or higher
- WordPress 5.0 or higher
- For PDF text extraction, the server should have `pdftotext` installed (from poppler-utils) or the Smalot PDF Parser library

## Changelog

### 1.0.0
- Initial release
- PDF upload and parsing
- Automatic break calculation
- Visual schedule table display
- Shortcode support

## License

MIT License
