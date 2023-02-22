"""
Minimalist type hint stub file for Flask-WTF to enable proper type checking with mypy.
"""

from wtforms import Form

class FlaskForm(Form):  # type: ignore[misc]
    ...
