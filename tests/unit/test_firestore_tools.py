from app.agent import list_smartphones, get_smartphone_details

def test_list_smartphones():
    phones = list_smartphones()
    assert isinstance(phones, list)
    assert len(phones) >= 4
    
    # Check Google filter
    google_phones = list_smartphones(brand="Google")
    assert all("google" in p["brand"].lower() for p in google_phones)

def test_get_smartphone_details():
    pixel = get_smartphone_details("Pixel 11 Pro")
    assert "error" not in pixel
    assert "Google Pixel 11 Pro" in pixel["model_name"]
    assert pixel["price"] == 999.0
    assert "features" in pixel
