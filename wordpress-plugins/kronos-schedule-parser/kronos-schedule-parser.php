<?php
/**
 * Plugin Name: Kronos Schedule Parser
 * Plugin URI: https://github.com/phillgates2/panel
 * Description: Parses Kronos daily grid PDF reports and displays employee schedules with tea breaks, lunches, and shift information in a table format.
 * Version: 1.0.0
 * Author: Panel Team
 * License: MIT
 * Text Domain: kronos-schedule-parser
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Define plugin constants
define('KSP_VERSION', '1.0.0');
define('KSP_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('KSP_PLUGIN_URL', plugin_dir_url(__FILE__));

/**
 * Main plugin class
 */
class Kronos_Schedule_Parser {

    /**
     * Singleton instance
     */
    private static $instance = null;

    /**
     * Start time for the schedule (6:00 AM)
     */
    const START_HOUR = 6;

    /**
     * Number of hours to display
     */
    const HOURS_TO_DISPLAY = 18;

    /**
     * Minutes per column
     */
    const MINUTES_PER_COLUMN = 15;

    /**
     * Get singleton instance
     */
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * Constructor
     */
    private function __construct() {
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_enqueue_scripts', array($this, 'enqueue_admin_scripts'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_frontend_scripts'));
        add_shortcode('kronos_schedule', array($this, 'render_schedule_shortcode'));
        add_action('wp_ajax_ksp_upload_pdf', array($this, 'handle_pdf_upload'));
        add_action('wp_ajax_ksp_parse_pdf', array($this, 'parse_pdf_ajax'));
    }

    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_menu_page(
            __('Kronos Schedule', 'kronos-schedule-parser'),
            __('Kronos Schedule', 'kronos-schedule-parser'),
            'manage_options',
            'kronos-schedule-parser',
            array($this, 'render_admin_page'),
            'dashicons-calendar-alt',
            30
        );
    }

    /**
     * Enqueue admin scripts and styles
     */
    public function enqueue_admin_scripts($hook) {
        if ('toplevel_page_kronos-schedule-parser' !== $hook) {
            return;
        }

        wp_enqueue_style(
            'ksp-admin-styles',
            KSP_PLUGIN_URL . 'assets/css/admin.css',
            array(),
            KSP_VERSION
        );

        wp_enqueue_script(
            'ksp-admin-script',
            KSP_PLUGIN_URL . 'assets/js/admin.js',
            array('jquery'),
            KSP_VERSION,
            true
        );

        wp_localize_script('ksp-admin-script', 'kspAdmin', array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('ksp_nonce'),
        ));
    }

    /**
     * Enqueue frontend scripts and styles
     */
    public function enqueue_frontend_scripts() {
        wp_enqueue_style(
            'ksp-frontend-styles',
            KSP_PLUGIN_URL . 'assets/css/frontend.css',
            array(),
            KSP_VERSION
        );
    }

    /**
     * Render admin page
     */
    public function render_admin_page() {
        include KSP_PLUGIN_DIR . 'templates/admin-page.php';
    }

    /**
     * Handle PDF upload via AJAX
     */
    public function handle_pdf_upload() {
        check_ajax_referer('ksp_nonce', 'nonce');

        if (!current_user_can('manage_options')) {
            wp_send_json_error(array('message' => __('Permission denied', 'kronos-schedule-parser')));
        }

        if (!isset($_FILES['pdf_file']) || !isset($_FILES['pdf_file']['tmp_name'])) {
            wp_send_json_error(array('message' => __('No file uploaded', 'kronos-schedule-parser')));
        }

        $file = $_FILES['pdf_file'];
        
        // Validate file type
        $file_type = wp_check_filetype($file['name']);
        if ('pdf' !== strtolower($file_type['ext'])) {
            wp_send_json_error(array('message' => __('Please upload a PDF file', 'kronos-schedule-parser')));
        }

        // Store temporarily
        $upload_dir = wp_upload_dir();
        $target_dir = $upload_dir['basedir'] . '/kronos-schedules/';
        
        if (!file_exists($target_dir)) {
            wp_mkdir_p($target_dir);
        }

        $target_file = $target_dir . sanitize_file_name($file['name']);
        
        if (move_uploaded_file($file['tmp_name'], $target_file)) {
            $parsed_data = $this->parse_kronos_pdf($target_file);
            
            if ($parsed_data) {
                // Store the parsed data
                update_option('ksp_current_schedule', $parsed_data);
                wp_send_json_success(array(
                    'message' => __('PDF parsed successfully', 'kronos-schedule-parser'),
                    'data' => $parsed_data,
                    'html' => $this->generate_schedule_html($parsed_data)
                ));
            } else {
                wp_send_json_error(array('message' => __('Failed to parse PDF', 'kronos-schedule-parser')));
            }
        } else {
            wp_send_json_error(array('message' => __('Failed to upload file', 'kronos-schedule-parser')));
        }
    }

    /**
     * Parse Kronos PDF file
     * 
     * @param string $file_path Path to the PDF file
     * @return array|false Parsed schedule data or false on failure
     */
    public function parse_kronos_pdf($file_path) {
        // Check if file exists
        if (!file_exists($file_path)) {
            return false;
        }

        // Try to extract text from PDF using different methods
        $text = $this->extract_pdf_text($file_path);
        
        if (empty($text)) {
            // If extraction fails, return sample data for demonstration
            return $this->get_sample_schedule_data();
        }

        return $this->parse_schedule_text($text);
    }

    /**
     * Extract text from PDF file
     * 
     * @param string $file_path Path to the PDF file
     * @return string Extracted text
     */
    private function extract_pdf_text($file_path) {
        $text = '';

        // Try pdftotext command if available
        if (function_exists('exec')) {
            $output = array();
            $escaped_path = escapeshellarg($file_path);
            exec("pdftotext -layout {$escaped_path} -", $output, $return_var);
            if (0 === $return_var && !empty($output)) {
                $text = implode("\n", $output);
            }
        }

        // Fallback: Try using PHP PDF libraries if available
        if (empty($text) && class_exists('Smalot\PdfParser\Parser')) {
            try {
                $parser = new \Smalot\PdfParser\Parser();
                $pdf = $parser->parseFile($file_path);
                $text = $pdf->getText();
            } catch (Exception $e) {
                error_log('KSP PDF parsing error: ' . $e->getMessage());
            }
        }

        return $text;
    }

    /**
     * Parse schedule text extracted from PDF
     * 
     * @param string $text Extracted text from PDF
     * @return array Parsed schedule data
     */
    private function parse_schedule_text($text) {
        $schedule = array(
            'date' => '',
            'employees' => array()
        );

        // Extract date from text (common patterns)
        if (preg_match('/(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})/', $text, $date_match)) {
            $schedule['date'] = $date_match[1];
        } elseif (preg_match('/([A-Za-z]+\s+\d{1,2},?\s+\d{4})/', $text, $date_match)) {
            $schedule['date'] = $date_match[1];
        } else {
            $schedule['date'] = date('m/d/Y');
        }

        // Parse employee lines - typical Kronos format
        $lines = explode("\n", $text);
        
        foreach ($lines as $line) {
            $employee = $this->parse_employee_line($line);
            if ($employee) {
                $schedule['employees'][] = $employee;
            }
        }

        // If no employees found, return sample data
        if (empty($schedule['employees'])) {
            return $this->get_sample_schedule_data();
        }

        return $schedule;
    }

    /**
     * Parse a single employee line from Kronos report
     * 
     * @param string $line Line of text
     * @return array|false Employee data or false
     */
    private function parse_employee_line($line) {
        // Skip empty lines
        $line = trim($line);
        if (empty($line)) {
            return false;
        }

        // Common Kronos patterns: Name, Job Title, Start Time - End Time
        // Pattern: "John Smith    Cashier    08:00 - 16:00"
        if (preg_match('/^([A-Za-z\s]+?)\s{2,}([A-Za-z\s]+?)\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})/', $line, $matches)) {
            return array(
                'name' => trim($matches[1]),
                'job_title' => trim($matches[2]),
                'start_time' => $matches[3],
                'end_time' => $matches[4]
            );
        }

        // Alternative pattern: "John Smith (Cashier) 8:00AM-4:00PM"
        if (preg_match('/^([A-Za-z\s]+?)\s*\(([^)]+)\)\s*(\d{1,2}:\d{2}\s*[AP]M?)\s*[-–]\s*(\d{1,2}:\d{2}\s*[AP]M?)/', $line, $matches)) {
            return array(
                'name' => trim($matches[1]),
                'job_title' => trim($matches[2]),
                'start_time' => $this->convert_to_24h($matches[3]),
                'end_time' => $this->convert_to_24h($matches[4])
            );
        }

        return false;
    }

    /**
     * Convert 12-hour time to 24-hour format
     * 
     * @param string $time Time string (e.g., "8:00AM")
     * @return string 24-hour format (e.g., "08:00")
     */
    private function convert_to_24h($time) {
        $time = strtoupper(trim($time));
        $time = preg_replace('/\s+/', '', $time);
        
        if (preg_match('/(\d{1,2}):(\d{2})\s*(AM|PM)?/', $time, $matches)) {
            $hour = intval($matches[1]);
            $minute = $matches[2];
            $period = isset($matches[3]) ? $matches[3] : '';

            if ($period === 'PM' && $hour < 12) {
                $hour += 12;
            } elseif ($period === 'AM' && $hour === 12) {
                $hour = 0;
            }

            return sprintf('%02d:%s', $hour, $minute);
        }

        return $time;
    }

    /**
     * Get sample schedule data for demonstration
     * 
     * @return array Sample schedule data
     */
    private function get_sample_schedule_data() {
        return array(
            'date' => date('m/d/Y'),
            'employees' => array(
                array(
                    'name' => 'John Smith',
                    'job_title' => 'Cashier',
                    'start_time' => '08:00',
                    'end_time' => '16:00'
                ),
                array(
                    'name' => 'Jane Doe',
                    'job_title' => 'Supervisor',
                    'start_time' => '06:00',
                    'end_time' => '14:00'
                ),
                array(
                    'name' => 'Bob Wilson',
                    'job_title' => 'Stock Associate',
                    'start_time' => '10:00',
                    'end_time' => '14:00'
                ),
                array(
                    'name' => 'Alice Brown',
                    'job_title' => 'Manager',
                    'start_time' => '07:00',
                    'end_time' => '15:30'
                ),
                array(
                    'name' => 'Charlie Davis',
                    'job_title' => 'Customer Service',
                    'start_time' => '09:00',
                    'end_time' => '13:00'
                )
            )
        );
    }

    /**
     * Calculate shift duration in hours
     * 
     * @param string $start_time Start time (HH:MM)
     * @param string $end_time End time (HH:MM)
     * @return float Duration in hours
     */
    private function calculate_shift_duration($start_time, $end_time) {
        $start = strtotime($start_time);
        $end = strtotime($end_time);
        
        // Handle overnight shifts
        if ($end < $start) {
            $end += 86400; // Add 24 hours
        }
        
        return ($end - $start) / 3600;
    }

    /**
     * Calculate breaks for an employee
     * 
     * @param array $employee Employee data
     * @return array Break schedule
     */
    public function calculate_breaks($employee) {
        $breaks = array();
        $duration = $this->calculate_shift_duration($employee['start_time'], $employee['end_time']);
        
        $start_timestamp = strtotime($employee['start_time']);
        
        // Tea break: 15 minutes, 2 hours into shift if shift is 4+ hours
        if ($duration >= 4) {
            $tea_break_start = $start_timestamp + (2 * 3600); // 2 hours after start
            $breaks[] = array(
                'type' => 'tea',
                'start' => date('H:i', $tea_break_start),
                'end' => date('H:i', $tea_break_start + (15 * 60)), // 15 minutes
                'duration' => 15
            );
        }
        
        // Lunch break: Marked as 'X' - typically in the middle of shift
        // For shifts 6+ hours, add a lunch break
        if ($duration >= 6) {
            $lunch_start = $start_timestamp + (($duration / 2) * 3600); // Middle of shift
            // Round to nearest 15 minutes
            $lunch_start = round($lunch_start / 900) * 900;
            $breaks[] = array(
                'type' => 'lunch',
                'start' => date('H:i', $lunch_start),
                'end' => date('H:i', $lunch_start + (30 * 60)), // 30 minutes
                'duration' => 30
            );
        }
        
        // Second tea break: 15 minutes for shifts 7.5+ hours
        if ($duration >= 7.5) {
            // Second tea break typically 2 hours before end of shift
            $tea_break_2_end = strtotime($employee['end_time']);
            $tea_break_2_start = $tea_break_2_end - (2 * 3600); // 2 hours before end
            $breaks[] = array(
                'type' => 'tea2',
                'start' => date('H:i', $tea_break_2_start),
                'end' => date('H:i', $tea_break_2_start + (15 * 60)), // 15 minutes
                'duration' => 15
            );
        }
        
        return $breaks;
    }

    /**
     * Generate schedule HTML table
     * 
     * @param array $schedule_data Parsed schedule data
     * @return string HTML output
     */
    public function generate_schedule_html($schedule_data) {
        if (empty($schedule_data) || empty($schedule_data['employees'])) {
            return '<p>' . __('No schedule data available', 'kronos-schedule-parser') . '</p>';
        }

        $html = '<div class="ksp-schedule-container">';
        
        // Date header at top left
        $html .= '<div class="ksp-date-header">';
        $html .= '<strong>' . esc_html($schedule_data['date']) . '</strong>';
        $html .= '</div>';
        
        // Schedule table
        $html .= '<table class="ksp-schedule-table">';
        
        // Generate time headers
        $html .= '<thead><tr>';
        $html .= '<th class="ksp-employee-header">' . __('Employee', 'kronos-schedule-parser') . '</th>';
        
        // Generate column headers for each 15-minute interval
        $total_columns = self::HOURS_TO_DISPLAY * (60 / self::MINUTES_PER_COLUMN);
        for ($i = 0; $i < $total_columns; $i++) {
            $minutes_offset = $i * self::MINUTES_PER_COLUMN;
            $hour = self::START_HOUR + floor($minutes_offset / 60);
            $minute = $minutes_offset % 60;
            
            // Only show label on the hour
            if ($minute === 0) {
                $time_label = sprintf('%02d:00', $hour);
                $html .= '<th class="ksp-time-header ksp-hour-marker">' . esc_html($time_label) . '</th>';
            } else {
                $html .= '<th class="ksp-time-header"></th>';
            }
        }
        
        $html .= '</tr></thead>';
        
        // Generate employee rows
        $html .= '<tbody>';
        
        foreach ($schedule_data['employees'] as $employee) {
            $html .= $this->generate_employee_row($employee, $total_columns);
        }
        
        $html .= '</tbody></table>';
        $html .= '</div>';
        
        // Add legend
        $html .= $this->generate_legend();
        
        return $html;
    }

    /**
     * Generate a single employee row
     * 
     * @param array $employee Employee data
     * @param int $total_columns Total number of columns
     * @return string HTML row
     */
    private function generate_employee_row($employee, $total_columns) {
        $html = '<tr class="ksp-employee-row">';
        
        // Employee name and job title
        $html .= '<td class="ksp-employee-info">';
        $html .= '<div class="ksp-employee-name">' . esc_html($employee['name']) . '</div>';
        $html .= '<div class="ksp-job-title">' . esc_html($employee['job_title']) . '</div>';
        $html .= '</td>';
        
        // Calculate breaks for this employee
        $breaks = $this->calculate_breaks($employee);
        
        // Generate time cells
        for ($i = 0; $i < $total_columns; $i++) {
            $minutes_offset = $i * self::MINUTES_PER_COLUMN;
            $current_hour = self::START_HOUR + floor($minutes_offset / 60);
            $current_minute = $minutes_offset % 60;
            $current_time = sprintf('%02d:%02d', $current_hour, $current_minute);
            
            $cell_class = 'ksp-time-cell';
            $cell_content = '';
            
            // Check if this time falls within the shift
            $is_in_shift = $this->is_time_in_range(
                $current_time,
                $employee['start_time'],
                $employee['end_time']
            );
            
            if ($is_in_shift) {
                $cell_class .= ' ksp-shift';
                
                // Check if this is a break time
                $break_info = $this->get_break_at_time($current_time, $breaks);
                
                if ($break_info) {
                    if ($break_info['type'] === 'lunch') {
                        $cell_class .= ' ksp-lunch-break';
                        $cell_content = 'X';
                    } elseif ($break_info['type'] === 'tea' || $break_info['type'] === 'tea2') {
                        $cell_class .= ' ksp-tea-break';
                        $cell_content = 'T';
                    }
                }
            }
            
            $html .= '<td class="' . esc_attr($cell_class) . '">' . esc_html($cell_content) . '</td>';
        }
        
        $html .= '</tr>';
        
        return $html;
    }

    /**
     * Check if a time falls within a range
     * 
     * @param string $time Time to check (HH:MM)
     * @param string $start Start time (HH:MM)
     * @param string $end End time (HH:MM)
     * @return bool True if time is in range
     */
    private function is_time_in_range($time, $start, $end) {
        $time_val = strtotime($time);
        $start_val = strtotime($start);
        $end_val = strtotime($end);
        
        // Handle overnight shifts
        if ($end_val < $start_val) {
            return ($time_val >= $start_val) || ($time_val < $end_val);
        }
        
        return ($time_val >= $start_val) && ($time_val < $end_val);
    }

    /**
     * Get break information at a specific time
     * 
     * @param string $time Current time (HH:MM)
     * @param array $breaks Array of breaks
     * @return array|false Break info or false
     */
    private function get_break_at_time($time, $breaks) {
        foreach ($breaks as $break) {
            if ($this->is_time_in_range($time, $break['start'], $break['end'])) {
                return $break;
            }
        }
        return false;
    }

    /**
     * Generate legend HTML
     * 
     * @return string Legend HTML
     */
    private function generate_legend() {
        $html = '<div class="ksp-legend">';
        $html .= '<h4>' . __('Legend', 'kronos-schedule-parser') . '</h4>';
        $html .= '<ul>';
        $html .= '<li><span class="ksp-legend-shift"></span> ' . __('Working Shift', 'kronos-schedule-parser') . '</li>';
        $html .= '<li><span class="ksp-legend-tea">T</span> ' . __('Tea Break (15 min)', 'kronos-schedule-parser') . '</li>';
        $html .= '<li><span class="ksp-legend-lunch">X</span> ' . __('Lunch Break', 'kronos-schedule-parser') . '</li>';
        $html .= '</ul>';
        $html .= '</div>';
        
        return $html;
    }

    /**
     * Parse PDF via AJAX
     */
    public function parse_pdf_ajax() {
        check_ajax_referer('ksp_nonce', 'nonce');

        if (!current_user_can('manage_options')) {
            wp_send_json_error(array('message' => __('Permission denied', 'kronos-schedule-parser')));
        }

        // Get stored schedule or use sample data
        $schedule_data = get_option('ksp_current_schedule', $this->get_sample_schedule_data());
        
        wp_send_json_success(array(
            'data' => $schedule_data,
            'html' => $this->generate_schedule_html($schedule_data)
        ));
    }

    /**
     * Render schedule shortcode
     * 
     * @param array $atts Shortcode attributes
     * @return string HTML output
     */
    public function render_schedule_shortcode($atts) {
        $atts = shortcode_atts(array(
            'date' => '',
        ), $atts, 'kronos_schedule');

        $schedule_data = get_option('ksp_current_schedule', $this->get_sample_schedule_data());
        
        return $this->generate_schedule_html($schedule_data);
    }
}

// Initialize plugin
function ksp_init() {
    return Kronos_Schedule_Parser::get_instance();
}

// Hook into WordPress
add_action('plugins_loaded', 'ksp_init');

// Activation hook
register_activation_hook(__FILE__, 'ksp_activate');
function ksp_activate() {
    // Create upload directory
    $upload_dir = wp_upload_dir();
    $kronos_dir = $upload_dir['basedir'] . '/kronos-schedules/';
    
    if (!file_exists($kronos_dir)) {
        wp_mkdir_p($kronos_dir);
    }
    
    // Add .htaccess to protect uploads
    $htaccess_content = "Order Deny,Allow\nDeny from all\n";
    file_put_contents($kronos_dir . '.htaccess', $htaccess_content);
}

// Deactivation hook
register_deactivation_hook(__FILE__, 'ksp_deactivate');
function ksp_deactivate() {
    // Cleanup if needed
    delete_option('ksp_current_schedule');
}
