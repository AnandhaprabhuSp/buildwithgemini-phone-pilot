"""Firestore client and helper functions for PhonePilot."""
from typing import Any, Dict, List, Optional
from google.cloud import firestore

# Hardcode the GCP Project ID as requested to prevent Agent Platform
# from returning the project number, which breaks Firestore client initialization.
PROJECT_ID = "qwiklabs-gcp-04-7d222e5d4be1"

_db_client: Optional[firestore.Client] = None

def get_db() -> firestore.Client:
    """Returns a singleton Firestore client instance."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=PROJECT_ID)
    return _db_client

def list_phones_from_db(brand: str = "") -> List[Dict[str, Any]]:
    """List phones from the Firestore database, optionally filtering by brand."""
    db = get_db()
    phones_ref = db.collection("phones")
    docs = phones_ref.stream()
    
    results = []
    brand_filter = brand.strip().lower() if brand else ""
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if not brand_filter or brand_filter in data.get("brand", "").lower():
            results.append(data)
    return results

def get_phone_specs_from_db(model_query: str) -> Optional[Dict[str, Any]]:
    """Get full phone specifications matching the query."""
    db = get_db()
    phones_ref = db.collection("phones")
    q_norm = model_query.strip().lower()
    
    # Try exact document id lookup first
    doc = phones_ref.document(q_norm.replace(" ", "-")).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
        
    # Search all phones for partial match
    docs = phones_ref.stream()
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        name = data.get("model_name", "").lower()
        doc_id = d.id.lower()
        if q_norm in name or q_norm in doc_id or name in q_norm:
            return data
    return None

def save_phone_to_db(phone_data: Dict[str, Any]) -> str:
    """Save or update a phone document in Firestore."""
    db = get_db()
    doc_id = phone_data.get("id") or phone_data.get("model_name", "").lower().replace(" ", "-")
    phone_data["id"] = doc_id
    db.collection("phones").document(doc_id).set(phone_data, merge=True)
    return doc_id

def save_trade_in_inquiry_to_db(inquiry_data: Dict[str, Any]) -> str:
    """Save a user trade-in inquiry to Firestore."""
    db = get_db()
    update_time, doc_ref = db.collection("trade_in_inquiries").add(inquiry_data)
    return doc_ref.id
