<?php
/**
 * Admin page template for Kronos Schedule Parser
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}
?>

<div class="wrap ksp-admin-container">
    <h1><?php esc_html_e('Kronos Schedule Parser', 'kronos-schedule-parser'); ?></h1>
    
    <p><?php esc_html_e('Upload a Kronos Daily Grid Report PDF to parse and display employee schedules with automatically calculated breaks.', 'kronos-schedule-parser'); ?></p>
    
    <!-- Upload Section -->
    <div class="ksp-upload-section">
        <h3><?php esc_html_e('Upload Kronos PDF Report', 'kronos-schedule-parser'); ?></h3>
        
        <form id="ksp-upload-form" enctype="multipart/form-data">
            <p>
                <input type="file" id="ksp-pdf-file" name="pdf_file" accept=".pdf,application/pdf" />
            </p>
            <p>
                <button type="submit" class="button button-primary">
                    <?php esc_html_e('Upload and Parse PDF', 'kronos-schedule-parser'); ?>
                </button>
                <button type="button" id="ksp-load-sample" class="button button-secondary">
                    <?php esc_html_e('Load Sample Data', 'kronos-schedule-parser'); ?>
                </button>
            </p>
        </form>
    </div>
    
    <!-- Messages -->
    <div id="ksp-messages"></div>
    
    <!-- Schedule Display -->
    <div id="ksp-schedule-display"></div>
    
    <!-- Break Rules Information -->
    <div class="ksp-break-rules" style="margin-top: 30px; padding: 20px; background: #e8f4fd; border-radius: 4px; border-left: 4px solid #2196F3;">
        <h4 style="margin-top: 0;"><?php esc_html_e('Automatic Break Calculation Rules:', 'kronos-schedule-parser'); ?></h4>
        <ul style="margin-bottom: 0;">
            <li><strong><?php esc_html_e('Tea Break (T):', 'kronos-schedule-parser'); ?></strong> 
                <?php esc_html_e('15 minutes, scheduled 2 hours into shift for shifts 4 hours or longer', 'kronos-schedule-parser'); ?>
            </li>
            <li><strong><?php esc_html_e('Lunch Break (X):', 'kronos-schedule-parser'); ?></strong> 
                <?php esc_html_e('Scheduled in the middle of shifts 6 hours or longer', 'kronos-schedule-parser'); ?>
            </li>
            <li><strong><?php esc_html_e('Second Tea Break (T):', 'kronos-schedule-parser'); ?></strong> 
                <?php esc_html_e('15 minutes, scheduled 2 hours before end of shift for shifts 7.5 hours or longer', 'kronos-schedule-parser'); ?>
            </li>
        </ul>
    </div>
    
    <!-- Shortcode Information -->
    <div class="ksp-shortcode-info">
        <h3><?php esc_html_e('Display Schedule on Your Site', 'kronos-schedule-parser'); ?></h3>
        <p><?php esc_html_e('Use this shortcode to display the parsed schedule on any page or post:', 'kronos-schedule-parser'); ?></p>
        <code>[kronos_schedule]</code>
    </div>
    
    <!-- Table Features Information -->
    <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px;">
        <h4 style="margin-top: 0;"><?php esc_html_e('Schedule Table Features:', 'kronos-schedule-parser'); ?></h4>
        <ul style="margin-bottom: 0;">
            <li><?php esc_html_e('Date displayed at top left of the schedule', 'kronos-schedule-parser'); ?></li>
            <li><?php esc_html_e('Each column represents 15 minutes, starting at 6:00 AM', 'kronos-schedule-parser'); ?></li>
            <li><?php esc_html_e('Employee name with job title shown below (styled in grey)', 'kronos-schedule-parser'); ?></li>
            <li><?php esc_html_e('Shifts displayed as greyed out cells', 'kronos-schedule-parser'); ?></li>
            <li><?php esc_html_e('Tea breaks marked with "T", lunches marked with "X"', 'kronos-schedule-parser'); ?></li>
        </ul>
    </div>
</div>
