"""
Authentication module for OAuth 2.0 client credentials flow.

This module provides functionality to obtain access tokens using the OAuth 2.0
client credentials grant type.
"""

import requests
from typing import Optional

__all__ = ['getToken']


def getToken(client_id: str, client_secret: str, auth_url: str) -> Optional[str]:
    """
    Get Oauth access token using client credentials flow.
    
    Args:
        client_id: The client ID (e.g., 'sb-xxxx')
        client_secret: The client secret
        auth_url: The authentication URL (e.g., 'https://xxxx.authentication.abc.com')
    
    Returns:
        Access token string if successful, None otherwise
    """
    try:
        # Prepare the token endpoint
        token_url = f"{auth_url}/oauth/token"
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'x-csrf-token': 'fetch'
        }
        
        # Prepare form data
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        # Make POST request
        response = requests.post(token_url, headers=headers, data=data)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Extract and return access token
        access_token = response.json().get('access_token')
        return access_token
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting token: {e}")
        return None