"""
RetainDB向量搜索客户端
实现语义相似度检索和历史咨询搜索
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

import numpy as np
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger()


class VectorDocument(BaseModel):
    """向量文档模型"""
    doc_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any]
    created_at: str = datetime.now().isoformat()


class RetainDBClient:
    """RetainDB向量搜索客户端"""
    
    def __init__(
        self,
        db_path: str = "./data/vectors",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85
    ):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.embedding_model_name = embedding_model
        self.similarity_threshold = similarity_threshold
        self.embedding_model = None
        self.documents: Dict[str, VectorDocument] = {}
        self.embeddings: Optional[np.ndarray] = None
        
    async def initialize(self):
        """初始化向量模型"""
        try:
            # 尝试加载sentence-transformers
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("向量模型加载成功", model=self.embedding_model_name)
        except ImportError:
            logger.warning("sentence-transformers未安装，使用简单的TF-IDF向量化")
            self.embedding_model = None
            
        # 加载已有文档
        self._load_documents()
        
    def _load_documents(self):
        """加载已有文档"""
        docs_file = self.db_path / "documents.json"
        
        if docs_file.exists():
            with open(docs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for doc_id, doc_data in data.items():
                    self.documents[doc_id] = VectorDocument(**doc_data)
                    
            # 重建嵌入矩阵
            if self.documents:
                embeddings = [doc.embedding for doc in self.documents.values() if doc.embedding]
                if embeddings:
                    self.embeddings = np.array(embeddings)
                    
            logger.info("加载向量文档", count=len(self.documents))
            
    def _save_documents(self):
        """保存文档"""
        docs_file = self.db_path / "documents.json"
        
        data = {
            doc_id: doc.model_dump()
            for doc_id, doc in self.documents.items()
        }
        
        with open(docs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本嵌入向量"""
        if self.embedding_model:
            embedding = self.embedding_model.encode(text)
            return embedding
        else:
            # 简单的词频向量化（仅用于演示）
            words = text.lower().split()
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # 创建固定长度的向量
            vector = np.zeros(384)  # 与MiniLM-L6-v2相同的维度
            for i, word in enumerate(word_freq.keys()):
                if i < 384:
                    vector[i] = word_freq[word]
                    
            # 归一化
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
                
            return vector
    
    async def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VectorDocument:
        """添加文档"""
        # 生成嵌入向量
        embedding = self._get_embedding(content)
        
        # 创建文档
        doc = VectorDocument(
            doc_id=doc_id,
            content=content,
            embedding=embedding.tolist(),
            metadata=metadata or {}
        )
        
        # 保存文档
        self.documents[doc_id] = doc
        
        # 更新嵌入矩阵
        if self.embeddings is None:
            self.embeddings = np.array([embedding])
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])
            
        # 保存到磁盘
        self._save_documents()
        
        logger.info("添加向量文档", doc_id=doc_id)
        return doc
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[VectorDocument, float]]:
        """搜索相似文档"""
        if not self.documents or self.embeddings is None:
            return []
            
        # 获取查询向量
        query_embedding = self._get_embedding(query)
        
        # 计算余弦相似度
        similarities = np.dot(self.embeddings, query_embedding)
        
        # 获取top-k索引
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # 构建结果列表
        results = []
        doc_list = list(self.documents.values())
        
        for idx in top_indices:
            doc = doc_list[idx]
            similarity = similarities[idx]
            
            # 应用过滤器
            if filters:
                match = all(
                    doc.metadata.get(key) == value
                    for key, value in filters.items()
                )
                if not match:
                    continue
                    
            # 应用相似度阈值
            if similarity >= self.similarity_threshold:
                results.append((doc, float(similarity)))
                
        logger.info("向量搜索完成", query=query[:50], results=len(results))
        return results
    
    async def delete_document(self, doc_id: str):
        """删除文档"""
        if doc_id not in self.documents:
            return
            
        # 删除文档
        del self.documents[doc_id]
        
        # 重建嵌入矩阵
        if self.documents:
            embeddings = [doc.embedding for doc in self.documents.values() if doc.embedding]
            if embeddings:
                self.embeddings = np.array(embeddings)
            else:
                self.embeddings = None
        else:
            self.embeddings = None
            
        # 保存到磁盘
        self._save_documents()
        
        logger.info("删除向量文档", doc_id=doc_id)
    
    async def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """更新文档"""
        if doc_id not in self.documents:
            raise ValueError(f"文档不存在: {doc_id}")
            
        doc = self.documents[doc_id]
        
        # 更新内容
        if content:
            doc.content = content
            doc.embedding = self._get_embedding(content).tolist()
            
        # 更新元数据
        if metadata:
            doc.metadata.update(metadata)
            
        # 重建嵌入矩阵
        embeddings = [doc.embedding for doc in self.documents.values() if doc.embedding]
        if embeddings:
            self.embeddings = np.array(embeddings)
            
        # 保存到磁盘
        self._save_documents()
        
        logger.info("更新向量文档", doc_id=doc_id)
    
    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        """获取文档"""
        return self.documents.get(doc_id)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_documents": len(self.documents),
            "embedding_dimension": self.embeddings.shape[1] if self.embeddings is not None else 0,
            "model": self.embedding_model_name
        }
