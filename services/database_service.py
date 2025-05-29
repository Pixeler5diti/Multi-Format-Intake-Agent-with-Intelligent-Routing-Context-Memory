"""
Database Service for Multi-Agent Document Processing System
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from models import ProcessingSession, EmailRecord, JSONExtraction, ConversationThread, AgentStats, get_db, create_tables
from models.schemas import ProcessingResult, ClassificationResult


class DatabaseService:
    """Service for database operations in the multi-agent system"""
    
    def __init__(self):
        # Create tables if they don't exist
        create_tables()
    
    def save_processing_session(self, result: ProcessingResult, db: Session) -> bool:
        """Save a processing session to the database"""
        try:
            session = ProcessingSession(
                processing_id=result.processing_id,
                timestamp=datetime.utcnow(),
                status=result.status,
                detected_format=result.classification.format,
                detected_intent=result.classification.intent,
                confidence_score=result.classification.confidence,
                classification_timestamp=datetime.fromisoformat(result.classification.timestamp),
                extracted_data=result.extracted_data,
                processing_metadata=result.metadata,
                error_message=result.classification.error
            )
            
            # Add file metadata if available
            if result.metadata:
                session.filename = result.metadata.get('filename')
                session.file_size = result.metadata.get('file_size')
                session.input_type = result.metadata.get('input_type', 'unknown')
            
            db.add(session)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error saving processing session: {str(e)}")
            return False
    
    def save_email_record(self, email_data: Dict[str, Any], processing_id: str, db: Session) -> bool:
        """Save an email record to the database"""
        try:
            contact = email_data.get('contact', {})
            email_details = email_data.get('email_details', {})
            request = email_data.get('request', {})
            priority = email_data.get('priority', {})
            processing = email_data.get('processing', {})
            
            record = EmailRecord(
                record_id=email_data.get('record_id', processing_id),
                processing_id=processing_id,
                conversation_id=email_data.get('conversation_id'),
                timestamp=datetime.utcnow(),
                
                # Contact information
                sender_email=contact.get('email'),
                sender_name=contact.get('name'),
                sender_organization=contact.get('organization'),
                sender_domain=contact.get('domain'),
                
                # Email details
                subject=email_details.get('subject'),
                date_sent=email_details.get('date'),
                message_id=email_details.get('message_id'),
                reply_to=email_details.get('reply_to'),
                
                # Intent analysis
                intent=request.get('intent'),
                request_summary=request.get('summary'),
                key_entities=request.get('key_entities', []),
                action_required=request.get('action_required'),
                sentiment=request.get('sentiment'),
                
                # Priority
                urgency_level=priority.get('urgency_level'),
                urgency_confidence=priority.get('urgency_confidence'),
                urgency_indicators=priority.get('urgency_indicators', {}),
                
                # Processing metadata
                extraction_confidence=processing.get('extraction_confidence'),
                requires_followup=processing.get('requires_followup', False),
                auto_categorized=processing.get('auto_categorized', True)
            )
            
            db.add(record)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error saving email record: {str(e)}")
            return False
    
    def save_json_extraction(self, json_data: Dict[str, Any], processing_id: str, db: Session) -> bool:
        """Save JSON extraction results to the database"""
        try:
            data_section = json_data.get('data', {})
            metadata_section = json_data.get('metadata', {})
            
            extraction = JSONExtraction(
                extraction_id=json_data.get('id', processing_id),
                processing_id=processing_id,
                timestamp=datetime.utcnow(),
                source_format=json_data.get('source', 'json'),
                extracted_fields=data_section.get('extracted', {}),
                important_entities=data_section.get('key_fields', []),
                key_fields=data_section.get('structure_analysis', {}),
                field_count=metadata_section.get('field_count', 0),
                anomalies=json_data.get('anomalies', []),
                flowbit_formatted=json_data,
                processing_confidence=json_data.get('confidence', 0.0),
                completeness_score=0.9,  # Default value, could be calculated
                schema_compliance=0.8    # Default value, could be calculated
            )
            
            db.add(extraction)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error saving JSON extraction: {str(e)}")
            return False
    
    def get_processing_sessions(self, limit: int = 50, db: Session = None) -> List[Dict[str, Any]]:
        """Retrieve recent processing sessions"""
        try:
            sessions = db.query(ProcessingSession)\
                       .order_by(ProcessingSession.timestamp.desc())\
                       .limit(limit)\
                       .all()
            
            return [
                {
                    'processing_id': session.processing_id,
                    'timestamp': session.timestamp.isoformat(),
                    'status': session.status,
                    'format': session.detected_format,
                    'intent': session.detected_intent,
                    'confidence': session.confidence_score,
                    'filename': session.filename,
                    'file_size': session.file_size
                }
                for session in sessions
            ]
            
        except Exception as e:
            print(f"Error retrieving processing sessions: {str(e)}")
            return []
    
    def get_email_records(self, limit: int = 50, db: Session = None) -> List[Dict[str, Any]]:
        """Retrieve recent email records"""
        try:
            records = db.query(EmailRecord)\
                       .order_by(EmailRecord.timestamp.desc())\
                       .limit(limit)\
                       .all()
            
            return [
                {
                    'record_id': record.record_id,
                    'sender_email': record.sender_email,
                    'sender_name': record.sender_name,
                    'subject': record.subject,
                    'intent': record.intent,
                    'urgency_level': record.urgency_level,
                    'timestamp': record.timestamp.isoformat(),
                    'conversation_id': record.conversation_id
                }
                for record in records
            ]
            
        except Exception as e:
            print(f"Error retrieving email records: {str(e)}")
            return []
    
    def get_conversation_history(self, conversation_id: str, db: Session = None) -> List[Dict[str, Any]]:
        """Get all records for a specific conversation"""
        try:
            records = db.query(EmailRecord)\
                       .filter(EmailRecord.conversation_id == conversation_id)\
                       .order_by(EmailRecord.timestamp.asc())\
                       .all()
            
            return [
                {
                    'record_id': record.record_id,
                    'sender_email': record.sender_email,
                    'subject': record.subject,
                    'intent': record.intent,
                    'timestamp': record.timestamp.isoformat(),
                    'request_summary': record.request_summary
                }
                for record in records
            ]
            
        except Exception as e:
            print(f"Error retrieving conversation history: {str(e)}")
            return []
    
    def update_conversation_thread(self, conversation_id: str, email_data: Dict[str, Any], db: Session) -> bool:
        """Update or create conversation thread"""
        try:
            thread = db.query(ConversationThread)\
                       .filter(ConversationThread.conversation_id == conversation_id)\
                       .first()
            
            if thread:
                # Update existing thread
                thread.updated_at = datetime.utcnow()
                thread.message_count += 1
                thread.last_activity = datetime.utcnow()
                
                # Update participant emails
                contact = email_data.get('contact', {})
                sender_email = contact.get('email')
                if sender_email:
                    participants = thread.participant_emails or []
                    if sender_email not in participants:
                        participants.append(sender_email)
                        thread.participant_emails = participants
            else:
                # Create new thread
                contact = email_data.get('contact', {})
                email_details = email_data.get('email_details', {})
                
                thread = ConversationThread(
                    conversation_id=conversation_id,
                    thread_subject=email_details.get('subject'),
                    participant_emails=[contact.get('email')] if contact.get('email') else [],
                    message_count=1,
                    last_activity=datetime.utcnow()
                )
                db.add(thread)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error updating conversation thread: {str(e)}")
            return False
    
    def get_agent_statistics(self, agent_name: str = None, db: Session = None) -> Dict[str, Any]:
        """Get agent performance statistics"""
        try:
            query = db.query(AgentStats)
            if agent_name:
                query = query.filter(AgentStats.agent_name == agent_name)
            
            stats = query.all()
            
            if not stats:
                return {
                    'total_processed': 0,
                    'success_rate': 0.0,
                    'average_confidence': 0.0,
                    'agents': {}
                }
            
            # Aggregate statistics
            total_processed = sum(s.documents_processed for s in stats)
            total_successful = sum(s.successful_extractions for s in stats)
            
            agent_stats = {}
            for stat in stats:
                if stat.agent_name not in agent_stats:
                    agent_stats[stat.agent_name] = {
                        'processed': 0,
                        'successful': 0,
                        'failed': 0,
                        'avg_confidence': 0.0
                    }
                
                agent_stats[stat.agent_name]['processed'] += stat.documents_processed
                agent_stats[stat.agent_name]['successful'] += stat.successful_extractions
                agent_stats[stat.agent_name]['failed'] += stat.failed_extractions
                agent_stats[stat.agent_name]['avg_confidence'] = stat.average_confidence
            
            return {
                'total_processed': total_processed,
                'success_rate': (total_successful / total_processed) if total_processed > 0 else 0.0,
                'agents': agent_stats
            }
            
        except Exception as e:
            print(f"Error retrieving agent statistics: {str(e)}")
            return {'error': str(e)}
    
    def health_check(self, db: Session = None) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            if db is None:
                return {'status': 'disconnected', 'error': 'No database connection'}
            
            # Simple query to test connection
            session_count = db.query(ProcessingSession).count()
            email_count = db.query(EmailRecord).count()
            
            return {
                'status': 'healthy',
                'processing_sessions': session_count,
                'email_records': email_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }