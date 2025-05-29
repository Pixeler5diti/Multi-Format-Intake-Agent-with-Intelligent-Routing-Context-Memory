"""
Shared Memory System - Lightweight in-memory storage for agent communication
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass, asdict
import json

from models.schemas import ClassificationResult


@dataclass
class MemoryEntry:
    """Individual memory entry structure"""
    processing_id: str
    timestamp: str
    metadata: Dict[str, Any]
    classification: Optional[ClassificationResult] = None
    extracted_data: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    agent_history: List[str] = None
    
    def __post_init__(self):
        if self.agent_history is None:
            self.agent_history = []


class SharedMemory:
    """Lightweight shared memory system for agent communication"""
    
    def __init__(self, max_entries: int = 1000, cleanup_hours: int = 24):
        self._memory: Dict[str, MemoryEntry] = {}
        self._conversation_index: Dict[str, List[str]] = {}  # conversation_id -> [processing_ids]
        self._lock = threading.RLock()
        self.max_entries = max_entries
        self.cleanup_hours = cleanup_hours
        
        # Statistics
        self._stats = {
            "total_entries": 0,
            "active_conversations": 0,
            "last_cleanup": datetime.utcnow().isoformat()
        }
    
    def store_metadata(self, processing_id: str, metadata: Dict[str, Any]) -> bool:
        """Store initial metadata for a processing session"""
        with self._lock:
            try:
                if processing_id not in self._memory:
                    self._memory[processing_id] = MemoryEntry(
                        processing_id=processing_id,
                        timestamp=datetime.utcnow().isoformat(),
                        metadata=metadata,
                        agent_history=["metadata_stored"]
                    )
                else:
                    # Update existing entry
                    self._memory[processing_id].metadata.update(metadata)
                    self._memory[processing_id].agent_history.append("metadata_updated")
                
                self._update_stats()
                self._cleanup_if_needed()
                return True
                
            except Exception as e:
                print(f"Error storing metadata: {str(e)}")
                return False
    
    def store_classification(self, processing_id: str, classification: ClassificationResult) -> bool:
        """Store classification result"""
        with self._lock:
            try:
                if processing_id not in self._memory:
                    self._memory[processing_id] = MemoryEntry(
                        processing_id=processing_id,
                        timestamp=datetime.utcnow().isoformat(),
                        metadata={},
                        classification=classification,
                        agent_history=["classification_stored"]
                    )
                else:
                    self._memory[processing_id].classification = classification
                    self._memory[processing_id].agent_history.append("classification_stored")
                
                self._update_stats()
                return True
                
            except Exception as e:
                print(f"Error storing classification: {str(e)}")
                return False
    
    def store_extracted_data(self, processing_id: str, extracted_data: Dict[str, Any]) -> bool:
        """Store extracted data from agents"""
        with self._lock:
            try:
                if processing_id not in self._memory:
                    self._memory[processing_id] = MemoryEntry(
                        processing_id=processing_id,
                        timestamp=datetime.utcnow().isoformat(),
                        metadata={},
                        extracted_data=extracted_data,
                        agent_history=["data_extracted"]
                    )
                else:
                    self._memory[processing_id].extracted_data = extracted_data
                    self._memory[processing_id].agent_history.append("data_extracted")
                
                self._update_stats()
                return True
                
            except Exception as e:
                print(f"Error storing extracted data: {str(e)}")
                return False
    
    def store_conversation_id(self, processing_id: str, conversation_id: str) -> bool:
        """Store conversation ID and update conversation index"""
        with self._lock:
            try:
                if processing_id not in self._memory:
                    self._memory[processing_id] = MemoryEntry(
                        processing_id=processing_id,
                        timestamp=datetime.utcnow().isoformat(),
                        metadata={},
                        conversation_id=conversation_id,
                        agent_history=["conversation_id_stored"]
                    )
                else:
                    self._memory[processing_id].conversation_id = conversation_id
                    self._memory[processing_id].agent_history.append("conversation_id_stored")
                
                # Update conversation index
                if conversation_id not in self._conversation_index:
                    self._conversation_index[conversation_id] = []
                
                if processing_id not in self._conversation_index[conversation_id]:
                    self._conversation_index[conversation_id].append(processing_id)
                
                self._update_stats()
                return True
                
            except Exception as e:
                print(f"Error storing conversation ID: {str(e)}")
                return False
    
    def get_memory(self, processing_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete memory entry for a processing ID"""
        with self._lock:
            entry = self._memory.get(processing_id)
            if entry:
                return self._serialize_entry(entry)
            return None
    
    def get_metadata(self, processing_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a processing ID"""
        with self._lock:
            entry = self._memory.get(processing_id)
            return entry.metadata if entry else None
    
    def get_classification(self, processing_id: str) -> Optional[ClassificationResult]:
        """Retrieve classification for a processing ID"""
        with self._lock:
            entry = self._memory.get(processing_id)
            return entry.classification if entry else None
    
    def get_extracted_data(self, processing_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve extracted data for a processing ID"""
        with self._lock:
            entry = self._memory.get(processing_id)
            return entry.extracted_data if entry else None
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieve all entries for a conversation ID"""
        with self._lock:
            processing_ids = self._conversation_index.get(conversation_id, [])
            history = []
            
            for pid in processing_ids:
                entry = self._memory.get(pid)
                if entry:
                    history.append(self._serialize_entry(entry))
            
            # Sort by timestamp
            history.sort(key=lambda x: x.get("timestamp", ""))
            return history
    
    def get_all_memory(self) -> Dict[str, Any]:
        """Retrieve all memory entries (for debugging/monitoring)"""
        with self._lock:
            return {
                "entries": {pid: self._serialize_entry(entry) for pid, entry in self._memory.items()},
                "conversation_index": self._conversation_index,
                "statistics": self._stats
            }
    
    def clear_memory(self, processing_id: str) -> bool:
        """Clear memory for a specific processing ID"""
        with self._lock:
            try:
                if processing_id in self._memory:
                    entry = self._memory[processing_id]
                    
                    # Remove from conversation index
                    if entry.conversation_id:
                        conv_list = self._conversation_index.get(entry.conversation_id, [])
                        if processing_id in conv_list:
                            conv_list.remove(processing_id)
                        if not conv_list:
                            del self._conversation_index[entry.conversation_id]
                    
                    # Remove main entry
                    del self._memory[processing_id]
                    self._update_stats()
                    return True
                
                return False
                
            except Exception as e:
                print(f"Error clearing memory: {str(e)}")
                return False
    
    def clear_all_memory(self) -> bool:
        """Clear all memory entries"""
        with self._lock:
            try:
                self._memory.clear()
                self._conversation_index.clear()
                self._update_stats()
                return True
            except Exception as e:
                print(f"Error clearing all memory: {str(e)}")
                return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        with self._lock:
            return {
                **self._stats,
                "current_entries": len(self._memory),
                "current_conversations": len(self._conversation_index),
                "memory_usage_mb": self._estimate_memory_usage(),
                "average_entry_size": self._estimate_memory_usage() / max(1, len(self._memory))
            }
    
    def _serialize_entry(self, entry: MemoryEntry) -> Dict[str, Any]:
        """Convert MemoryEntry to serializable dictionary"""
        result = asdict(entry)
        
        # Handle ClassificationResult serialization
        if entry.classification:
            result["classification"] = asdict(entry.classification)
        
        return result
    
    def _update_stats(self):
        """Update internal statistics"""
        self._stats.update({
            "total_entries": len(self._memory),
            "active_conversations": len(self._conversation_index),
            "last_update": datetime.utcnow().isoformat()
        })
    
    def _cleanup_if_needed(self):
        """Clean up old entries if needed"""
        current_count = len(self._memory)
        
        # Clean up if we exceed max entries
        if current_count > self.max_entries:
            self._cleanup_old_entries()
        
        # Periodic cleanup based on time
        last_cleanup = datetime.fromisoformat(self._stats["last_cleanup"])
        if datetime.utcnow() - last_cleanup > timedelta(hours=self.cleanup_hours):
            self._cleanup_expired_entries()
    
    def _cleanup_old_entries(self):
        """Remove oldest entries to stay within max_entries limit"""
        if len(self._memory) <= self.max_entries:
            return
        
        # Sort entries by timestamp
        sorted_entries = sorted(
            self._memory.items(),
            key=lambda x: x[1].timestamp
        )
        
        # Remove oldest entries
        entries_to_remove = len(self._memory) - self.max_entries + 100  # Remove extra for buffer
        
        for i in range(min(entries_to_remove, len(sorted_entries))):
            processing_id = sorted_entries[i][0]
            self.clear_memory(processing_id)
    
    def _cleanup_expired_entries(self):
        """Remove entries older than cleanup_hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.cleanup_hours)
        expired_ids = []
        
        for processing_id, entry in self._memory.items():
            try:
                entry_time = datetime.fromisoformat(entry.timestamp)
                if entry_time < cutoff_time:
                    expired_ids.append(processing_id)
            except ValueError:
                # If timestamp is invalid, consider it expired
                expired_ids.append(processing_id)
        
        for processing_id in expired_ids:
            self.clear_memory(processing_id)
        
        self._stats["last_cleanup"] = datetime.utcnow().isoformat()
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB (rough approximation)"""
        try:
            total_chars = 0
            for entry in self._memory.values():
                # Rough estimation based on string representation
                total_chars += len(str(entry))
            
            # Approximate bytes (assuming average 2 bytes per character for mixed content)
            estimated_bytes = total_chars * 2
            return estimated_bytes / (1024 * 1024)  # Convert to MB
            
        except Exception:
            return 0.0
