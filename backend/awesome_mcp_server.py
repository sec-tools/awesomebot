#!/usr/bin/env python3
"""
AwesomeBot Multi-Function MCP Server
=====================================

A comprehensive MCP server providing essential system and utility tools
for AwesomeBot users.

Features:
- Weather information for any city
- Current date/time with timezone support
- System update checking via apt package manager

This server follows the Model Context Protocol (MCP) specification
and provides seamless integration with AwesomeBot and other MCP-compatible
AI systems.

Author: AwesomeBot Community
Version: 1.0.0
License: MIT
"""

import sys
import json
import subprocess
import datetime
from typing import Dict, Any

class AwesomeMCPServer:
    """
    Multi-function MCP server for AwesomeBot
    
    Provides weather, datetime, and system maintenance tools
    """
    
    def __init__(self):
        self.server_info = {
            "name": "awesome_mcp_server",
            "version": "1.0.0",
            "description": "Multi-function MCP server for AwesomeBot"
        }
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": self.server_info
        }
    
    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return list of available tools"""
        return {
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get current weather information for any city worldwide",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "Name of the city (e.g., 'New York', 'London', 'Tokyo')"
                            }
                        },
                        "required": ["city"]
                    }
                },
                {
                    "name": "get_datetime",
                    "description": "Get current date and time with optional timezone",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "Timezone identifier (default: UTC)",
                                "default": "UTC"
                            }
                        }
                    }
                },
                {
                    "name": "check_updates",
                    "description": "Check for available system package updates using apt package manager. Helps keep your system secure and up-to-date.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package": {
                                "type": "string",
                                "description": "Optional: specify a particular package name to check for updates (e.g., 'nginx', 'python3'). Leave empty to check all packages.",
                                "default": ""
                            }
                        }
                    }
                }
            ]
        }
    
    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool based on name"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "get_weather":
            return self.tool_get_weather(arguments)
        elif tool_name == "get_datetime":
            return self.tool_get_datetime(arguments)
        elif tool_name == "check_updates":
            return self.tool_check_updates(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def tool_get_weather(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get weather information for a specified city
        
        Returns current temperature and weather conditions.
        In production, this would integrate with a real weather API.
        """
        city = arguments.get("city", "Unknown")
        
        # Weather data mapping
        weather_data = {
            "New York": {"temp": 68, "condition": "Partly Cloudy", "humidity": "65%", "wind": "10 mph"},
            "London": {"temp": 59, "condition": "Rainy", "humidity": "80%", "wind": "15 mph"},
            "Tokyo": {"temp": 72, "condition": "Sunny", "humidity": "55%", "wind": "8 mph"},
            "Paris": {"temp": 63, "condition": "Overcast", "humidity": "70%", "wind": "12 mph"},
            "Sydney": {"temp": 75, "condition": "Clear", "humidity": "60%", "wind": "5 mph"},
            "Berlin": {"temp": 61, "condition": "Cloudy", "humidity": "68%", "wind": "14 mph"},
            "Moscow": {"temp": 55, "condition": "Cold", "humidity": "75%", "wind": "18 mph"},
            "Singapore": {"temp": 86, "condition": "Humid", "humidity": "85%", "wind": "6 mph"}
        }
        
        weather = weather_data.get(city, {"temp": 70, "condition": "Unknown", "humidity": "N/A", "wind": "N/A"})
        
        return {
            "content": [{
                "type": "text",
                "text": f"🌤️  Weather Report for {city}\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                       f"Temperature: {weather['temp']}°F\n"
                       f"Condition: {weather['condition']}\n"
                       f"Humidity: {weather['humidity']}\n"
                       f"Wind Speed: {weather['wind']}"
            }]
        }
    
    def tool_get_datetime(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current date and time
        
        Returns formatted date/time with timezone information.
        """
        timezone = arguments.get("timezone", "UTC")
        
        now = datetime.datetime.now()
        
        # Format the date in a clear English format
        weekday = now.strftime('%A')
        month = now.strftime('%B')
        day = now.day
        year = now.year
        time_str = now.strftime('%H:%M:%S')
        
        return {
            "content": [{
                "type": "text",
                "text": f"## 🕐 Current Date & Time ({timezone})\n\n"
                       f"| Field | Value |\n"
                       f"|-------|-------|\n"
                       f"| **Date** | {weekday}, {month} {day}, {year} |\n"
                       f"| **Time** | {time_str} |\n"
                       f"| **ISO Format** | {now.isoformat()} |\n"
                       f"| **Unix Timestamp** | {int(now.timestamp())} |\n\n"
                       f"Today is **{weekday}, {month} {day}, {year}** and the current time is **{time_str}** ({timezone})."
            }]
        }
    
    def tool_check_updates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for system package updates
        
        Uses the apt package manager to check for available updates.
        Helps keep your system secure with the latest packages.
        
        Args:
            arguments: Dict containing optional 'package' parameter
        
        Returns:
            Dict with content containing update information
        """
        package = arguments.get("package", "")
        
        # Build apt command to check for updates
        if package:
            # Check specific package
            cmd = f"apt list --upgradable {package} 2>&1"
            pkg_desc = f"for package `{package}`"
        else:
            # Check all packages
            cmd = "apt list --upgradable 2>&1"
            pkg_desc = "for all packages"
        
        try:
            # Execute apt command
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Collect all output
            full_output = ""
            if result.stdout:
                full_output += result.stdout
            if result.stderr:
                full_output += result.stderr
            
            # Count upgradable packages
            lines = [l for l in full_output.split('\n') if l.strip() and 'Listing' not in l and 'WARNING' not in l]
            upgrade_count = len(lines)
            
            # Determine status
            if upgrade_count == 0:
                status = f"✅ **No updates available** {pkg_desc}. Your system is up to date!"
            else:
                status = f"📦 **{upgrade_count} package(s) available for upgrade** {pkg_desc}."
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"## 🔄 System Update Check\n\n"
                           f"{status}\n\n"
                           f"### Console Output\n\n"
                           f"```\n"
                           f"$ {cmd}\n"
                           f"{full_output}"
                           f"```\n\n"
                           f"*Command executed: `{cmd}`*"
                }]
            }
            
        except subprocess.TimeoutExpired:
            return {
                "content": [{
                    "type": "text",
                    "text": "## 🔄 System Update Check\n\n"
                           "⏱️ **Timeout**: The update check took too long. Please try again later.\n\n"
                           f"*Command attempted: `{cmd}`*"
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"## 🔄 System Update Check\n\n"
                           f"❌ **Error**: {str(e)}\n\n"
                           f"Please ensure apt is properly configured.\n\n"
                           f"*Command attempted: `{cmd}`*"
                }]
            }
    
    def run(self):
        """Main MCP server loop - reads JSON-RPC from stdin, writes to stdout"""
        for line in sys.stdin:
            try:
                # Parse JSON-RPC request
                request = json.loads(line.strip())
                method = request.get("method")
                params = request.get("params", {})
                request_id = request.get("id")
                
                # Handle request based on method
                if method == "initialize":
                    result = self.handle_initialize(params)
                elif method == "tools/list":
                    result = self.handle_tools_list(params)
                elif method == "tools/call":
                    result = self.handle_tools_call(params)
                else:
                    # Unknown method
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    print(json.dumps(response), flush=True)
                    continue
                
                # Success response
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
                
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                # Invalid JSON
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
            except Exception as e:
                # Other errors
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if 'request' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    print("🚀 AwesomeBot Multi-Function MCP Server v1.0.0", file=sys.stderr)
    print("   Starting server...", file=sys.stderr)
    
    server = AwesomeMCPServer()
    server.run()
