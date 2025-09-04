from abc import ABC, abstractmethod
from collections import deque
from typing import List, Dict, Any
import threading
import asyncio
import time
import datetime
import logging
from ..api._manager import connection_manager
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)

class ChatHandler(ABC):
    """Abstract base class for all chat handlers"""
    
    def __init__(self):
        self.is_connected = False
        self.comment_queue = deque()
        self.loop = None
        self.loop_thread = None
        
    @abstractmethod
    def connect(self, identifier: str) -> bool:
        """Connect to live stream"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from live stream"""
        pass
    
    @abstractmethod
    def _run_event_loop(self, identifier: str):
        """Run platform-specific event loop"""
        pass
    
    def get_new_comments(self) -> List[Dict[str, Any]]:
        """Get new comments from queue"""
        try:
            comments = []
            while self.comment_queue:
                comments.append(self.comment_queue.popleft())
            return comments
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return []
    
    def process_comments_for_importance(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and filter important comments"""
        if not comments:
            return []
        
        important_comments = []
        keywords = [
            "giá", "bao nhiêu", "price", "cost", "ship", "giao hàng", 
            "chất lượng", "quality", "bảo hành", "warranty", "còn hàng",
            "available", "mua", "buy", "order", "đặt hàng", "tư vấn",
            "advice", "giảm giá", "discount", "khuyến mãi", "promotion",
            "thanh toán", "payment", "size", "màu", "color"
        ]
        
        for comment in comments:
            message = comment.get("message", "").lower()
            if any(keyword in message for keyword in keywords) or "?" in message:
                comment["priority"] = "high" if "?" in message else "medium"
                important_comments.append(comment)
        
        if not important_comments and comments:
            recent_comments = comments[-3:]
            for comment in recent_comments:
                comment["priority"] = "low"
                important_comments.append(comment)
        
        return important_comments[:5]
    
    def _cleanup_connection(self):
        """Common cleanup logic"""
        self.is_connected = False
        if self.loop_thread and self.loop_thread.is_alive():
            if self.loop:
                self.loop.call_soon_threadsafe(self.loop.stop)
        self.comment_queue.clear()


class YouTubeChatHandler(ChatHandler):
    """YouTube Live Chat Handler"""
    
    def __init__(self):
        super().__init__()
        self.livechat = None
        
    def connect(self, video_id: str) -> bool:
        """Connect to YouTube live stream"""
        try:
            if self.is_connected:
                return True
                
            logger.info(f"Connecting to YouTube live stream: {video_id}")
            
            self.loop_thread = threading.Thread(target=self._run_event_loop, args=(video_id,))
            self.loop_thread.daemon = True
            self.loop_thread.start()
            
            time.sleep(2)
            return self.is_connected
            
        except Exception as e:
            logger.error(f"Error connecting to YouTube: {e}")
            return False
    
    def _run_event_loop(self, video_id: str):
        """Run YouTube event loop"""
        try:
            import pytchat
            
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.livechat = pytchat.create(video_id=video_id, interruptable=False)
            self.is_connected = True
            logger.info(f"Connected to YouTube live stream: {video_id}")
            
            while self.livechat.is_alive() and self.is_connected:
                try:
                    for c in self.livechat.get().sync_items():
                        if not self.is_connected:
                            break
                            
                        comment_data = {
                            "author": c.author.name,
                            "message": c.message,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        comment_data['id'] = comment_data["author"] + comment_data["timestamp"]
                        self.comment_queue.append(comment_data)
                        logger.info(f"YouTube Comment [{c.author.name}]: {c.message}")
                        
                        try:
                            # push cho client websocket
                            logger.info("Sending comments through websocket...")
                            target_loop = getattr(connection_manager, "loop", None)
                            if not target_loop:
                                logger.warning("connection_manager.loop not set; broadcast may fail. Please set it on FastAPI startup.")
                                target_loop = asyncio.get_event_loop()
                            asyncio.run_coroutine_threadsafe(
                                connection_manager.broadcast(
                                    json.dumps({"type": "live_comment", "comment": comment_data})
                                ),
                                target_loop
                            )
                            logger.info("Sent comments through websocket...")
                        except Exception as e:
                            logger.error(f"Error while sending comments through websocket: {e}")
                            raise e
                except Exception as e:
                    logger.error(f"Error processing YouTube comments: {e}")
                    time.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error in YouTube event loop: {e}")
            self.is_connected = False
    
    def disconnect(self) -> bool:
        """Disconnect from YouTube live stream"""
        try:
            self._cleanup_connection()
            if self.livechat:
                self.livechat.terminate()
            logger.info("Disconnected from YouTube live stream")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from YouTube: {e}")
            return False
        
class TikTokChatHandler(ChatHandler):
    """TikTok Live Chat Handler"""
    
    def __init__(self):
        super().__init__()
        self.client = None
        
    def connect(self, unique_id: str) -> bool:
        """Connect to TikTok live stream"""
        try:
            if self.is_connected:
                logger.info("TikTok already connected")
                return True
                
            # Clean username
            unique_id = unique_id.replace('@', '').strip()
            
            if not unique_id:
                logger.error("Empty TikTok username provided")
                return False
                
            logger.info(f"Connecting to TikTok live stream: @{unique_id}")
            
            # Start event loop thread
            self.loop_thread = threading.Thread(target=self._run_event_loop, args=(unique_id,))
            self.loop_thread.daemon = True
            self.loop_thread.start()
            
            # Wait longer for TikTok connection
            time.sleep(10)
            
            logger.info(f"TikTok connection status: {self.is_connected}")
            return self.is_connected
            
        except Exception as e:
            logger.error(f"Error connecting to TikTok: {e}", exc_info=True)
            return False
    
    def _run_event_loop(self, unique_id: str):
        """Run TikTok event loop"""
        try:
            # Import TikTok libraries
            try:
                from TikTokLive import TikTokLiveClient
                from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent
            except ImportError as e:
                logger.error(f"TikTokLive library not installed: {e}")
                return
            
            # Create new event loop
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            logger.info(f"Creating TikTok client for: @{unique_id}")
            
            # Create TikTok client with better error handling
            try:
                self.client = TikTokLiveClient(unique_id=f"@{unique_id}")
            except Exception as e:
                logger.error(f"Failed to create TikTok client: {e}")
                return
            
            # Connection event handler
            @self.client.on(ConnectEvent)
            async def on_connect(event: ConnectEvent):
                logger.info(f"Successfully connected to TikTok @{event.unique_id}")
                self.is_connected = True
            
            # Comment event handler
            @self.client.on(CommentEvent)
            async def on_comment(event: CommentEvent):
                try:
                    comment_data = {
                        "author": event.user.nickname,
                        "message": event.comment,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    comment_data['id'] = comment_data["author"] + comment_data["timestamp"]
                    self.comment_queue.append(comment_data)
                    logger.info(f"TikTok Comment [{event.user.nickname}]: {event.comment}")
                        
                    try:
                        # push cho client websocket
                        logger.info("Sending comments through websocket...")
                        target_loop = getattr(connection_manager, "loop", None)
                        if not target_loop:
                            logger.warning("connection_manager.loop not set; broadcast may fail. Please set it on FastAPI startup.")
                            target_loop = asyncio.get_event_loop()
                        asyncio.run_coroutine_threadsafe(
                            connection_manager.broadcast(
                                json.dumps({"type": "live_comment", "comment": comment_data})
                            ),
                            target_loop
                        )
                        logger.info("Sent comments through websocket...")
                    except Exception as e:
                        logger.error(f"Error while sending comments through websocket: {e}")
                        raise e
                
                except Exception as e:
                    logger.error(f"Error processing TikTok comment: {e}")
            
            # Disconnect event handler
            @self.client.on(DisconnectEvent)
            async def on_disconnect(event: DisconnectEvent):
                logger.info("TikTok client disconnected")
                self.is_connected = False
            
            # Start the client with timeout
            logger.info("Starting TikTok client...")
            
            try:
                self.loop.run_until_complete(self.client.run())
            except Exception as e:
                logger.error(f"Error starting TikTok client: {e}")
                self.is_connected = False
            
        except Exception as e:
            logger.error(f"Error in TikTok event loop: {e}", exc_info=True)
            self.is_connected = False
        finally:
            logger.info("TikTok event loop ended")
    
    def disconnect(self) -> bool:
        """Disconnect from TikTok live stream"""
        try:
            logger.info("Disconnecting from TikTok live stream")
            
            self.is_connected = False
            
            # Stop client
            if self.client:
                try:
                    if self.loop and self.loop.is_running():
                        asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
                    else:
                        # If loop is not running, create a new one to disconnect
                        asyncio.run(self.client.disconnect())
                except Exception as e:
                    logger.warning(f"Error stopping TikTok client: {e}")
            
            # Stop event loop
            if self.loop and self.loop.is_running():
                try:
                    self.loop.call_soon_threadsafe(self.loop.stop)
                except Exception as e:
                    logger.warning(f"Error stopping event loop: {e}")
            
            # Wait for thread
            if self.loop_thread and self.loop_thread.is_alive():
                self.loop_thread.join(timeout=5)
            
            # Clear queue
            self.comment_queue.clear()
            
            logger.info("Successfully disconnected from TikTok live stream")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from TikTok: {e}")
            return False     
        
class ChatHandlerFactory:
    """Factory pattern for creating chat handlers"""
    
    _handlers = {
        'youtube': YouTubeChatHandler,
        'tiktok': TikTokChatHandler
    }
    
    @classmethod
    def create_handler(cls, platform: str) -> ChatHandler:
        """Create chat handler for specified platform"""
        if platform.lower() not in cls._handlers:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return cls._handlers[platform.lower()]()
    
    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """Get list of supported platforms"""
        return list(cls._handlers.keys())


class ChatManager:
    """Main chat manager using Strategy pattern"""
    
    def __init__(self):
        self.handlers = {}
        self.current_platform = None
        self.current_handler = None
        
    def set_platform(self, platform: str) -> bool:
        """Set current platform and create handler if needed"""
        try:
            if platform not in self.handlers:
                self.handlers[platform] = ChatHandlerFactory.create_handler(platform)
            
            # Disconnect current handler if different platform
            if self.current_platform and self.current_platform != platform:
                self.disconnect()
            
            self.current_platform = platform
            self.current_handler = self.handlers[platform]
            return True
            
        except Exception as e:
            logger.error(f"Error setting platform {platform}: {e}")
            return False
    
    def connect(self, identifier: str) -> bool:
        """Connect to current platform"""
        if not self.current_handler:
            logger.error("No platform selected")
            return False
        return self.current_handler.connect(identifier)
    
    def disconnect(self) -> bool:
        """Disconnect from current platform"""
        if not self.current_handler:
            return True
        
        return self.current_handler.disconnect()
    
    def get_new_comments(self) -> List[Dict[str, Any]]:
        """Get new comments from current platform"""
        if not self.current_handler:
            return []
        
        return self.current_handler.get_new_comments()
    
    def is_connected(self) -> bool:
        """Check if current handler is connected"""
        if not self.current_handler:
            return False
        
        return self.current_handler.is_connected
    
    def get_current_platform(self) -> str:
        """Get current platform name"""
        return self.current_platform or "none"
    
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms"""
        return ChatHandlerFactory.get_supported_platforms()