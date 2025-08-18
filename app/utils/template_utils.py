# app/utils/__init__.py
# Empty file to make this a package

# app/utils/template_utils.py
import logging
from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Jinja2 environment
template_dir = settings.TEMPLATE_DIR
template_dir.mkdir(exist_ok=True, parents=True)

jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml'])
)


def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """Render email template with context"""
    try:
        template = jinja_env.get_template(template_name)
        
        # Add default context values
        default_context = {
            'company_name': settings.COMPANY_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'app_name': settings.PROJECT_NAME,
            'current_year': 2025,
        }
        
        # Merge contexts
        merged_context = {**default_context, **context}
        
        return template.render(**merged_context)
        
    except Exception as e:
        logger.error(f"Template rendering failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Template rendering failed: {str(e)}"
        )