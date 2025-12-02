/**
 * Kronos Schedule Parser - Admin JavaScript
 */

(function($) {
    'use strict';

    var KSPAdmin = {
        /**
         * Initialize admin functionality
         */
        init: function() {
            this.bindEvents();
            this.loadExistingSchedule();
        },

        /**
         * Bind event handlers
         */
        bindEvents: function() {
            $('#ksp-upload-form').on('submit', this.handleUpload.bind(this));
            $('#ksp-load-sample').on('click', this.loadSampleData.bind(this));
        },

        /**
         * Handle PDF upload
         */
        handleUpload: function(e) {
            e.preventDefault();

            var fileInput = $('#ksp-pdf-file')[0];
            
            if (!fileInput.files || !fileInput.files[0]) {
                this.showMessage('Please select a PDF file to upload.', 'error');
                return;
            }

            var file = fileInput.files[0];
            
            // Validate file type
            if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
                this.showMessage('Please select a valid PDF file.', 'error');
                return;
            }

            var formData = new FormData();
            formData.append('action', 'ksp_upload_pdf');
            formData.append('nonce', kspAdmin.nonce);
            formData.append('pdf_file', file);

            this.showLoading();

            $.ajax({
                url: kspAdmin.ajaxUrl,
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    this.hideLoading();
                    
                    if (response.success) {
                        this.showMessage('Schedule parsed successfully!', 'success');
                        this.displaySchedule(response.data.html);
                    } else {
                        this.showMessage(response.data.message || 'Failed to parse PDF.', 'error');
                    }
                }.bind(this),
                error: function(xhr, status, error) {
                    this.hideLoading();
                    this.showMessage('An error occurred while uploading the file.', 'error');
                    console.error('Upload error:', error);
                }.bind(this)
            });
        },

        /**
         * Load sample data for demonstration
         */
        loadSampleData: function(e) {
            e.preventDefault();

            this.showLoading();

            $.ajax({
                url: kspAdmin.ajaxUrl,
                type: 'POST',
                data: {
                    action: 'ksp_parse_pdf',
                    nonce: kspAdmin.nonce
                },
                success: function(response) {
                    this.hideLoading();
                    
                    if (response.success) {
                        this.showMessage('Sample schedule loaded successfully!', 'success');
                        this.displaySchedule(response.data.html);
                    } else {
                        this.showMessage('Failed to load sample data.', 'error');
                    }
                }.bind(this),
                error: function(xhr, status, error) {
                    this.hideLoading();
                    this.showMessage('An error occurred while loading sample data.', 'error');
                    console.error('Load error:', error);
                }.bind(this)
            });
        },

        /**
         * Load existing schedule if available
         */
        loadExistingSchedule: function() {
            $.ajax({
                url: kspAdmin.ajaxUrl,
                type: 'POST',
                data: {
                    action: 'ksp_parse_pdf',
                    nonce: kspAdmin.nonce
                },
                success: function(response) {
                    if (response.success && response.data.html) {
                        this.displaySchedule(response.data.html);
                    }
                }.bind(this)
            });
        },

        /**
         * Display schedule HTML
         */
        displaySchedule: function(html) {
            $('#ksp-schedule-display').html(html);
        },

        /**
         * Show loading indicator
         */
        showLoading: function() {
            var loading = '<div class="ksp-loading">' +
                '<span class="spinner is-active"></span>' +
                '<p>Processing schedule...</p>' +
                '</div>';
            $('#ksp-schedule-display').html(loading);
        },

        /**
         * Hide loading indicator
         */
        hideLoading: function() {
            $('.ksp-loading').remove();
        },

        /**
         * Show message to user
         */
        showMessage: function(message, type) {
            var $container = $('#ksp-messages');
            var className = 'ksp-message ksp-message-' + type;
            var $message = $('<div class="' + className + '">' + message + '</div>');
            
            $container.empty().append($message);
            
            // Auto-hide success messages
            if (type === 'success') {
                setTimeout(function() {
                    $message.fadeOut(function() {
                        $(this).remove();
                    });
                }, 5000);
            }
        }
    };

    // Initialize when document is ready
    $(document).ready(function() {
        KSPAdmin.init();
    });

})(jQuery);
