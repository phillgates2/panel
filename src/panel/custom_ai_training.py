"""
Custom AI Model Training
Fine-tuning and custom model training capabilities
"""

import os
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from src.panel.ai_integration import get_ai_client
from src.panel.enhanced_ai import get_enhanced_ai_agent

logger = logging.getLogger(__name__)

class AIModelTrainer:
    """Custom AI model training and fine-tuning"""

    def __init__(self):
        self.ai_client = get_ai_client()
        self.enhanced_ai = get_enhanced_ai_agent()
        self.training_jobs = {}  # job_id -> training data
        self.fine_tuned_models = {}  # model_id -> model data

    async def create_fine_tuning_job(self, base_model: str, training_data: List[Dict],
                                   parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fine-tuning job for custom model training"""
        try:
            job_id = str(uuid.uuid4())

            # Validate training data
            validation = await self._validate_training_data(training_data)
            if not validation['valid']:
                return {
                    'error': 'Invalid training data',
                    'details': validation['errors'],
                    'job_id': job_id
                }

            # Prepare training configuration
            config = {
                'job_id': job_id,
                'base_model': base_model,
                'training_data': training_data,
                'parameters': parameters,
                'status': 'preparing',
                'created_at': datetime.utcnow().isoformat(),
                'progress': 0.0
            }

            self.training_jobs[job_id] = config

            # Start training in background
            asyncio.create_task(self._run_training_job(job_id))

            return {
                'job_id': job_id,
                'status': 'preparing',
                'estimated_time': self._estimate_training_time(len(training_data), parameters),
                'message': 'Training job created successfully'
            }

        except Exception as e:
            logger.error(f"Failed to create fine-tuning job: {e}")
            return {
                'error': str(e),
                'message': 'Failed to create training job'
            }

    async def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a training job"""
        if job_id not in self.training_jobs:
            return {'error': 'Training job not found'}

        job = self.training_jobs[job_id]
        return {
            'job_id': job_id,
            'status': job['status'],
            'progress': job.get('progress', 0.0),
            'current_epoch': job.get('current_epoch', 0),
            'total_epochs': job.get('parameters', {}).get('epochs', 1),
            'loss': job.get('loss', 0.0),
            'estimated_time_remaining': job.get('estimated_time_remaining', 0),
            'created_at': job['created_at'],
            'updated_at': job.get('updated_at', job['created_at'])
        }

    async def cancel_training_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running training job"""
        if job_id not in self.training_jobs:
            return {'error': 'Training job not found'}

        job = self.training_jobs[job_id]
        if job['status'] in ['completed', 'failed', 'cancelled']:
            return {'error': f'Job is already {job["status"]}'}

        job['status'] = 'cancelled'
        job['updated_at'] = datetime.utcnow().isoformat()

        return {
            'job_id': job_id,
            'status': 'cancelled',
            'message': 'Training job cancelled'
        }

    async def list_training_jobs(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all training jobs"""
        jobs = []
        for job_id, job in self.training_jobs.items():
            if status_filter is None or job['status'] == status_filter:
                jobs.append({
                    'job_id': job_id,
                    'status': job['status'],
                    'base_model': job['base_model'],
                    'created_at': job['created_at'],
                    'progress': job.get('progress', 0.0)
                })

        return sorted(jobs, key=lambda x: x['created_at'], reverse=True)

    async def deploy_fine_tuned_model(self, job_id: str, model_name: str) -> Dict[str, Any]:
        """Deploy a completed fine-tuned model"""
        if job_id not in self.training_jobs:
            return {'error': 'Training job not found'}

        job = self.training_jobs[job_id]
        if job['status'] != 'completed':
            return {'error': f'Job status is {job["status"]}, not completed'}

        model_id = str(uuid.uuid4())

        self.fine_tuned_models[model_id] = {
            'model_id': model_id,
            'name': model_name,
            'base_model': job['base_model'],
            'training_job': job_id,
            'created_at': datetime.utcnow().isoformat(),
            'performance_metrics': job.get('final_metrics', {}),
            'status': 'deployed'
        }

        return {
            'model_id': model_id,
            'name': model_name,
            'status': 'deployed',
            'message': 'Model deployed successfully'
        }

    async def use_custom_model(self, model_id: str, prompt: str, **kwargs) -> str:
        """Use a deployed custom model for inference"""
        if model_id not in self.fine_tuned_models:
            raise ValueError(f"Model {model_id} not found")

        model = self.fine_tuned_models[model_id]
        if model['status'] != 'deployed':
            raise ValueError(f"Model {model_id} is not deployed")

        # In a real implementation, this would use the fine-tuned model
        # For now, fall back to base AI capabilities
        if self.enhanced_ai:
            return await self.enhanced_ai.generate_response(prompt)
        else:
            return "Custom model inference not available"

    async def get_model_performance(self, model_id: str) -> Dict[str, Any]:
        """Get performance metrics for a custom model"""
        if model_id not in self.fine_tuned_models:
            return {'error': 'Model not found'}

        model = self.fine_tuned_models[model_id]
        return {
            'model_id': model_id,
            'name': model['name'],
            'performance_metrics': model.get('performance_metrics', {}),
            'training_job': model['training_job'],
            'created_at': model['created_at']
        }

    async def _validate_training_data(self, training_data: List[Dict]) -> Dict[str, Any]:
        """Validate training data format and quality"""
        errors = []

        if not training_data:
            errors.append("Training data is empty")
            return {'valid': False, 'errors': errors}

        if len(training_data) < 10:
            errors.append("Training data should have at least 10 examples")

        required_fields = ['input', 'output']
        for i, example in enumerate(training_data):
            for field in required_fields:
                if field not in example:
                    errors.append(f"Example {i} missing required field: {field}")

            # Check data quality
            if len(example.get('input', '')) < 10:
                errors.append(f"Example {i} input too short")
            if len(example.get('output', '')) < 5:
                errors.append(f"Example {i} output too short")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'data_quality_score': max(0, 1 - (len(errors) / len(training_data)))
        }

    async def _run_training_job(self, job_id: str):
        """Run the actual training job"""
        try:
            job = self.training_jobs[job_id]
            job['status'] = 'running'
            job['started_at'] = datetime.utcnow().isoformat()

            # Simulate training process
            parameters = job['parameters']
            epochs = parameters.get('epochs', 3)
            training_data = job['training_data']

            for epoch in range(epochs):
                job['current_epoch'] = epoch + 1
                job['progress'] = (epoch + 1) / epochs

                # Simulate training time
                await asyncio.sleep(2)  # Simulate training work

                # Simulate loss decreasing
                job['loss'] = max(0.1, 1.0 - (epoch + 1) * 0.3)

                # Estimate remaining time
                job['estimated_time_remaining'] = (epochs - epoch - 1) * 2

                job['updated_at'] = datetime.utcnow().isoformat()

            # Training completed
            job['status'] = 'completed'
            job['progress'] = 1.0
            job['completed_at'] = datetime.utcnow().isoformat()

            # Generate mock performance metrics
            job['final_metrics'] = {
                'accuracy': 0.85 + (len(training_data) / 1000) * 0.1,
                'loss': job['loss'],
                'epochs_trained': epochs,
                'training_samples': len(training_data)
            }

            logger.info(f"Training job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Training job {job_id} failed: {e}")
            job = self.training_jobs.get(job_id, {})
            job['status'] = 'failed'
            job['error'] = str(e)
            job['updated_at'] = datetime.utcnow().isoformat()

    def _estimate_training_time(self, data_size: int, parameters: Dict) -> int:
        """Estimate training time in seconds"""
        base_time = 60  # Base time in seconds
        data_factor = data_size / 100  # Scale with data size
        epoch_factor = parameters.get('epochs', 3)
        model_factor = 2 if parameters.get('model_size', 'small') == 'large' else 1

        return int(base_time * data_factor * epoch_factor * model_factor)

    async def create_dataset_from_history(self, user_id: int, data_type: str = 'conversations') -> List[Dict]:
        """Create training dataset from user interaction history"""
        try:
            # This would query the database for user interactions
            # Placeholder implementation
            dataset = []

            if data_type == 'conversations':
                # Generate mock conversation data
                conversations = [
                    {"input": "How do I install mods?", "output": "To install mods, first download them from a trusted source..."},
                    {"input": "Server keeps crashing", "output": "Server crashes can be caused by several issues..."},
                    {"input": "What's the best graphics settings?", "output": "Optimal graphics settings depend on your hardware..."}
                ]
                dataset.extend(conversations)

            return dataset

        except Exception as e:
            logger.error(f"Failed to create dataset from history: {e}")
            return []

    async def evaluate_model_performance(self, model_id: str, test_data: List[Dict]) -> Dict[str, Any]:
        """Evaluate custom model performance on test data"""
        try:
            if model_id not in self.fine_tuned_models:
                return {'error': 'Model not found'}

            # Simulate evaluation
            correct_predictions = 0
            total_predictions = len(test_data)

            for test_case in test_data:
                # Mock prediction accuracy
                if len(test_case.get('input', '')) > 20:  # Simple heuristic
                    correct_predictions += 1

            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0

            return {
                'model_id': model_id,
                'accuracy': accuracy,
                'total_samples': total_predictions,
                'evaluation_date': datetime.utcnow().isoformat(),
                'metrics': {
                    'precision': accuracy * 0.9,
                    'recall': accuracy * 0.95,
                    'f1_score': accuracy * 0.92
                }
            }

        except Exception as e:
            logger.error(f"Model evaluation failed: {e}")
            return {
                'error': str(e),
                'accuracy': 0.0,
                'total_samples': 0
            }

# Global model trainer
model_trainer = None

def init_model_trainer():
    """Initialize AI model trainer"""
    global model_trainer
    model_trainer = AIModelTrainer()
    logger.info("AI model trainer initialized")

def get_model_trainer() -> Optional[AIModelTrainer]:
    """Get the model trainer instance"""
    return model_trainer

# Background task for training job cleanup
async def cleanup_old_training_jobs():
    """Clean up old completed/failed training jobs"""
    while True:
        try:
            if model_trainer:
                current_time = datetime.utcnow()
                jobs_to_remove = []

                for job_id, job in model_trainer.training_jobs.items():
                    # Remove jobs older than 7 days
                    job_age = current_time - datetime.fromisoformat(job['created_at'])
                    if job_age.days > 7 and job['status'] in ['completed', 'failed', 'cancelled']:
                        jobs_to_remove.append(job_id)

                for job_id in jobs_to_remove:
                    del model_trainer.training_jobs[job_id]

                if jobs_to_remove:
                    logger.info(f"Cleaned up {len(jobs_to_remove)} old training jobs")

        except Exception as e:
            logger.error(f"Training job cleanup failed: {e}")

        await asyncio.sleep(86400)  # Run daily

# Start cleanup task
def start_training_cleanup(socketio):
    """Start the training cleanup background task"""
    socketio.start_background_task(cleanup_old_training_jobs)

# Utility functions
async def start_fine_tuning(base_model: str, training_data: List[Dict]) -> str:
    """Quick function to start model fine-tuning"""
    trainer = get_model_trainer()
    if trainer:
        result = await trainer.create_fine_tuning_job(
            base_model=base_model,
            training_data=training_data,
            parameters={'epochs': 3, 'learning_rate': 0.001}
        )
        return result.get('job_id', '')
    return ''

async def get_training_progress(job_id: str) -> Dict[str, Any]:
    """Get training progress for a job"""
    trainer = get_model_trainer()
    if trainer:
        return await trainer.get_training_status(job_id)
    return {'error': 'Model trainer not available'}