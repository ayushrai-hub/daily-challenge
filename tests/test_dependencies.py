"""
This file tests that all required dependencies are properly installed and can be imported.
"""

def test_fastapi_imports():
    """Test that FastAPI dependencies can be imported."""
    from fastapi import FastAPI, Depends, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from fastapi.middleware.cors import CORSMiddleware
    assert FastAPI is not None
    assert Depends is not None
    assert HTTPException is not None
    assert status is not None
    assert OAuth2PasswordBearer is not None
    assert CORSMiddleware is not None


def test_sqlalchemy_imports():
    """Test that SQLAlchemy dependencies can be imported."""
    from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, relationship
    assert create_engine is not None
    assert Column is not None
    assert Integer is not None
    assert String is not None
    assert ForeignKey is not None
    assert declarative_base is not None
    assert sessionmaker is not None
    assert relationship is not None


def test_pydantic_imports():
    """Test that Pydantic dependencies can be imported."""
    from pydantic import BaseModel, Field, validator
    assert BaseModel is not None
    assert Field is not None
    assert validator is not None


def test_security_imports():
    """Test that security dependencies can be imported."""
    from jose import jwt
    from passlib.context import CryptContext
    assert jwt is not None
    assert CryptContext is not None


def test_http_imports():
    """Test that HTTP client dependencies can be imported."""
    import httpx
    assert httpx is not None


def test_app_core_imports():
    """Test that app core utilities can be imported."""
    from app.core.security import verify_password, get_password_hash, create_access_token
    assert verify_password is not None
    assert get_password_hash is not None
    assert create_access_token is not None