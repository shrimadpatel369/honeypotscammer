"""Training API - Fast Kaggle Dataset Integration"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.training_manager import training_manager
from app.auth import verify_api_key
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["AI Training & Learning"])


class TrainingExample(BaseModel):
    """Single training example"""
    scammer_message: str
    effective_response: Optional[str] = None
    scam_type: str = "unknown"
    notes: Optional[str] = None


class BulkUpload(BaseModel):
    """Bulk training data"""
    examples: List[TrainingExample]


@router.post("/upload")
async def upload_training_data(
    data: BulkUpload,
    api_key: str = Depends(verify_api_key)
):
    """
    Upload training examples manually
    
    Example:
    ```json
    {
      "examples": [
        {
          "scammer_message": "Your account is blocked",
          "effective_response": "Which account? I have multiple banks",
          "scam_type": "bank_phishing"
        }
      ]
    }
    ```
    """
    try:
        examples = [ex.model_dump() for ex in data.examples]
        success = await training_manager.store_examples(examples, source="manual")
        
        return {
            "success": success,
            "count": len(examples),
            "message": f"Added {len(examples)} training examples"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Import Kaggle CSV dataset
    
    Expected columns: text, type, label, category
    """
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files allowed")
        
        # Save temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Import
        result = await training_manager.import_kaggle_csv(tmp_path)
        os.unlink(tmp_path)
        
        if result['success']:
            return {
                "success": True,
                "count": result['count'],
                "file": file.filename,
                "message": f"Imported {result['count']} examples from {file.filename}"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Import failed'))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-json")
async def import_json(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Import Kaggle JSON dataset
    
    Expected format: array of objects with scam examples
    """
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files allowed")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        result = await training_manager.import_kaggle_json(tmp_path)
        os.unlink(tmp_path)
        
        if result['success']:
            return {
                "success": True,
                "count": result['count'],
                "file": file.filename,
                "message": f"Imported {result['count']} examples"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error'))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(api_key: str = Depends(verify_api_key)):
    """
    Get training statistics
    
    Shows how many examples from Kaggle vs live learning
    """
    try:
        stats = await training_manager.get_statistics()
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_examples(
    scam_type: Optional[str] = None,
    limit: int = 10,
    api_key: str = Depends(verify_api_key)
):
    """View stored training examples"""
    try:
        examples = await training_manager.get_relevant_examples(
            scam_type=scam_type,
            limit=limit
        )
        
        # Clean for display
        for ex in examples:
            ex.pop('_id', None)
        
        return {
            "success": True,
            "count": len(examples),
            "examples": examples
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
