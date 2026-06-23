"""
Minimal Trusted Kernel (MTK) - SQLite Authorizer Hook.
Physical runtime coercion that prevents state mutation unless explicitly authorized.
"""
from .authorizer import (
    mtk_authorizer_callback, 
    install_mtk_authorizer, 
    mtk_active_token, 
    mtk_payload_hash,
    set_token_verifier
)

__all__ = [
    "mtk_authorizer_callback",
    "install_mtk_authorizer",
    "mtk_active_token",
    "mtk_payload_hash",
    "set_token_verifier"
]
