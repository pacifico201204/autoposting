"""
Settings Manager - Handle app configuration UI and persistence
Features:
  - Display all config settings in a user-friendly UI
  - Edit settings without restart
  - Real-time validation
  - Auto-save to config.yaml
"""

import yaml
import os
import sys
from logger_config import log_info, log_error, log_warning
import flet as ft
from utils import get_resource_path


class SettingsManager:
    """Manage app settings UI and persistence"""

    def __init__(self, config_file="config.yaml"):
        self.config_file = get_resource_path(config_file)
        self.current_config = self._load_config()
        self.ui_elements = {}  # Store UI element references
        self.app_ui = None  # Reference to AppUI for callbacks

    def _load_config(self):
        """Load config from YAML file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            # Fall back to current directory if resource path doesn't work
            elif os.path.exists("config.yaml"):
                with open("config.yaml", 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {}
        except Exception as e:
            log_error(f"Failed to load config: {e}")
            return {}

    def _save_config(self):
        """Save config to YAML file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.current_config, f, allow_unicode=True,
                          default_flow_style=False)
            log_info(f"✅ Settings saved")
            return True
        except Exception as e:
            log_error(f"Failed to save config: {e}")
            return False

    def _on_setting_changed(self, e, key_path, input_elem):
        """Handle setting value change (supports TextField and Switch)"""
        try:
            # Get value - handle both TextField (with .strip()) and Switch (boolean)
            if isinstance(input_elem.value, bool):
                # Switch control - value is already boolean
                value = input_elem.value
            else:
                # TextField control - need to parse
                value = input_elem.value.strip()

                # Parse value based on type
                if value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif '.' in value and all(c.isdigit() or c == '.' for c in value):
                    try:
                        value = float(value)
                    except:
                        pass  # Keep as string

            # Update config using key_path (e.g., "delays.post_min")
            keys = key_path.split('.')
            config = self.current_config
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            config[keys[-1]] = value

            # Save changes
            self._save_config()

        except Exception as e:
            log_error(f"Failed to change setting: {e}")

    def build_settings_ui(self, colors):
        """Build the settings UI"""
        sections = []

        # Helper function to create setting row
        def create_setting_row(label, key_path, current_value, help_text=""):
            """Create a single setting input row"""
            input_field = ft.TextField(
                label=label,
                value=str(current_value),
                border_color=colors["border"],
                color=colors["text_main"],
                label_style=ft.TextStyle(color=colors["text_muted"]),
                on_change=lambda e: self._on_setting_changed(
                    e, key_path, input_field)
            )

            row_content = [input_field]
            if help_text:
                row_content.append(
                    ft.Text(help_text, size=11,
                            color=colors["text_muted"], italic=True)
                )

            return ft.Column(row_content, spacing=3)

        # === DELAYS SECTION ===
        delays_col = ft.Column([
            ft.Text("⏱️  Auto-Posting Delays", size=14,
                    weight="bold", color=colors["accent"]),
            ft.Divider(color=colors["border"]),
            create_setting_row(
                "Min Delay (seconds)",
                "delays.post_min",
                self.current_config.get("delays", {}).get("post_min", 5),
                "Minimum seconds between posts"
            ),
            create_setting_row(
                "Max Delay (seconds)",
                "delays.post_max",
                self.current_config.get("delays", {}).get("post_max", 10),
                "Maximum seconds between posts"
            ),
        ], spacing=10)

        # === SAFETY THRESHOLDS SECTION ===
        safety_col = ft.Column([
            ft.Text("🛡️  Safety Thresholds", size=14,
                    weight="bold", color=colors["accent"]),
            ft.Divider(color=colors["border"]),
            create_setting_row(
                "Max Posts Per Session",
                "detection.max_posts_per_session",
                self.current_config.get("detection", {}).get(
                    "max_posts_per_session", 10),
                "Maximum posts to send in one run"
            ),
            create_setting_row(
                "Max Posts Per Day",
                "detection.max_posts_per_day",
                self.current_config.get("detection", {}).get(
                    "max_posts_per_day", 25),
                "Maximum posts allowed in one day"
            ),
            create_setting_row(
                "Min Delay Between Sessions (seconds)",
                "detection.min_delay_between_sessions",
                self.current_config.get("detection", {}).get(
                    "min_delay_between_sessions", 300),
                "Minimum seconds to wait between runs"
            ),
            create_setting_row(
                "Max Delay Between Sessions (seconds)",
                "detection.max_delay_between_sessions",
                self.current_config.get("detection", {}).get(
                    "max_delay_between_sessions", 1800),
                "Maximum seconds to wait between runs"
            ),
            create_setting_row(
                "Min Delay Between Posts (seconds)",
                "detection.min_delay_between_posts",
                self.current_config.get("detection", {}).get(
                    "min_delay_between_posts", 5),
                "Minimum seconds between each post"
            ),
        ], spacing=10)

        # Dry Run Mode Toggle (without Application Settings header)
        dry_run_value = self.current_config.get(
            "app", {}).get("dry_run", False)
        dry_run_toggle = ft.Switch(
            label="🧪 Dry Run Mode (Test without posting)",
            value=dry_run_value,
            on_change=lambda e: self._on_setting_changed(
                e, "app.dry_run", dry_run_toggle),
            active_color=colors["accent"]
        )

        # Combine all sections
        settings_content = ft.Column([
            delays_col,
            ft.Divider(color=colors["border"], height=20),
            safety_col,
            ft.Divider(color=colors["border"], height=20),
            dry_run_toggle,
            ft.Text("Test all steps without actually posting to Facebook",
                    size=11, color=colors["text_muted"], italic=True),
            ft.Container(height=20),  # Spacer
        ], spacing=15, scroll="auto")

        return settings_content
