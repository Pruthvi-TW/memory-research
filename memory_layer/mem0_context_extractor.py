"""
Lending Context Extractor for extracting structured text from /Lending folder.
Compatible with the existing lending folder structure and data format.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class Mem0ContextExtractor:
    """
    Extracts structured context from the Lending directory structure.
    Handles capabilities, common prompts, and OpenAPI specifications.
    """
    
    def __init__(self, lending_dir: str = "../Lending"):
        """
        Initialize the context extractor.
        
        Args:
            lending_dir: Path to the Lending directory
        """
        self.lending_dir = Path(lending_dir)
        
        if not self.lending_dir.exists():
            logger.warning(f"⚠️ Lending directory not found: {lending_dir}")
            
    def extract_all_context(self) -> Dict[str, Any]:
        """
        Extract all context from the Lending directory.
        
        Returns:
            Dictionary containing all extracted context data
        """
        context_data = {
            "capabilities": {},
            "common_prompts": {},
            "openapi_specs": {}
        }
        
        try:
            # Extract capabilities
            context_data["capabilities"] = self._extract_capabilities()
            
            # Extract common prompts
            context_data["common_prompts"] = self._extract_common_prompts()
            
            # Extract OpenAPI specs
            context_data["openapi_specs"] = self._extract_openapi_specs()
            
            logger.info(f"✅ Extracted context from {self.lending_dir}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting context: {e}")
            
        return context_data
        
    def _extract_capabilities(self) -> Dict[str, Any]:
        """Extract capabilities from the Capabilities directory"""
        capabilities = {}
        capabilities_dir = self.lending_dir / "Capabilities"
        
        if not capabilities_dir.exists():
            logger.warning(f"⚠️ Capabilities directory not found: {capabilities_dir}")
            return capabilities
            
        try:
            for cap_dir in capabilities_dir.iterdir():
                if cap_dir.is_dir():
                    cap_name = cap_dir.name.lower()
                    capabilities[cap_name] = {
                        "prompts": self._read_prompts(cap_dir),
                        "specs": self._read_specs(cap_dir)
                    }
                    
            logger.info(f"📁 Extracted {len(capabilities)} capabilities")
            
        except Exception as e:
            logger.error(f"❌ Error extracting capabilities: {e}")
            
        return capabilities
        
    def _read_prompts(self, cap_dir: Path) -> Dict[str, str]:
        """Read prompts from original-prompt and mock-prompt directories"""
        prompts = {}
        
        # Read from original-prompt directory
        original_prompt_dir = cap_dir / "original-prompt"
        if original_prompt_dir.exists():
            for prompt_file in original_prompt_dir.glob("*.txt"):
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        prompts[f"original_{prompt_file.stem}"] = f.read()
                except Exception as e:
                    logger.error(f"❌ Error reading {prompt_file}: {e}")
                    
        # Read from mock-prompt directory
        mock_prompt_dir = cap_dir / "mock-prompt"
        if mock_prompt_dir.exists():
            for prompt_file in mock_prompt_dir.glob("*.txt"):
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        prompts[f"mock_{prompt_file.stem}"] = f.read()
                except Exception as e:
                    logger.error(f"❌ Error reading {prompt_file}: {e}")
                    
        return prompts
        
    def _read_specs(self, cap_dir: Path) -> Dict[str, Any]:
        """Read OpenAPI specs from original-code/swagger and mock-code/swagger directories"""
        specs = {}
        
        # Read from original-code/swagger directory
        original_swagger_dir = cap_dir / "original-code" / "swagger"
        if original_swagger_dir.exists():
            for spec_file in original_swagger_dir.glob("*.yaml"):
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        specs[f"original_{spec_file.stem}"] = yaml.safe_load(f)
                except Exception as e:
                    logger.error(f"❌ Error reading {spec_file}: {e}")
                    
            # Also check for .yml files
            for spec_file in original_swagger_dir.glob("*.yml"):
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        specs[f"original_{spec_file.stem}"] = yaml.safe_load(f)
                except Exception as e:
                    logger.error(f"❌ Error reading {spec_file}: {e}")
                    
        # Read from mock-code/swagger directory
        mock_swagger_dir = cap_dir / "mock-code" / "swagger"
        if mock_swagger_dir.exists():
            for spec_file in mock_swagger_dir.glob("*.yaml"):
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        specs[f"mock_{spec_file.stem}"] = yaml.safe_load(f)
                except Exception as e:
                    logger.error(f"❌ Error reading {spec_file}: {e}")
                    
            # Also check for .yml files
            for spec_file in mock_swagger_dir.glob("*.yml"):
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        specs[f"mock_{spec_file.stem}"] = yaml.safe_load(f)
                except Exception as e:
                    logger.error(f"❌ Error reading {spec_file}: {e}")
                    
        return specs
        
    def _extract_common_prompts(self) -> Dict[str, str]:
        """Extract common prompts from CommonPrompts directory"""
        common_prompts = {}
        common_prompts_dir = self.lending_dir / "CommonPrompts"
        
        if not common_prompts_dir.exists():
            logger.warning(f"⚠️ CommonPrompts directory not found: {common_prompts_dir}")
            return common_prompts
            
        try:
            for prompt_file in common_prompts_dir.glob("*.txt"):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    common_prompts[prompt_file.stem] = f.read()
                    
            logger.info(f"📄 Extracted {len(common_prompts)} common prompts")
            
        except Exception as e:
            logger.error(f"❌ Error extracting common prompts: {e}")
            
        return common_prompts
        
    def _extract_openapi_specs(self) -> Dict[str, Any]:
        """Extract standalone OpenAPI specs from the root level"""
        openapi_specs = {}
        
        try:
            # Look for OpenAPI specs in the root Lending directory
            for spec_file in self.lending_dir.glob("*.yaml"):
                if "openapi" in spec_file.name.lower() or "swagger" in spec_file.name.lower():
                    try:
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            openapi_specs[spec_file.stem] = yaml.safe_load(f)
                    except Exception as e:
                        logger.error(f"❌ Error reading {spec_file}: {e}")
                        
            # Also check for .yml files
            for spec_file in self.lending_dir.glob("*.yml"):
                if "openapi" in spec_file.name.lower() or "swagger" in spec_file.name.lower():
                    try:
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            openapi_specs[spec_file.stem] = yaml.safe_load(f)
                    except Exception as e:
                        logger.error(f"❌ Error reading {spec_file}: {e}")
                        
            if openapi_specs:
                logger.info(f"📋 Extracted {len(openapi_specs)} OpenAPI specs")
                
        except Exception as e:
            logger.error(f"❌ Error extracting OpenAPI specs: {e}")
            
        return openapi_specs
        
    def get_context_summary(self) -> str:
        """
        Get a human-readable summary of the extracted context.
        
        Returns:
            Formatted summary string
        """
        context_data = self.extract_all_context()
        
        summary_lines = ["Lending System Context Summary:", "=" * 40]
        
        # Capabilities summary
        if context_data["capabilities"]:
            summary_lines.append("\nAvailable Capabilities:")
            for cap_name, cap_data in context_data["capabilities"].items():
                prompt_count = len(cap_data.get("prompts", {}))
                spec_count = len(cap_data.get("specs", {}))
                summary_lines.append(f"  - {cap_name}: {prompt_count} prompts, {spec_count} specs")
        else:
            summary_lines.append("\nNo capabilities found")
            
        # Common prompts summary
        if context_data["common_prompts"]:
            summary_lines.append(f"\nCommon Guidelines: {len(context_data['common_prompts'])} files")
            for prompt_name in context_data["common_prompts"].keys():
                summary_lines.append(f"  - {prompt_name}")
        else:
            summary_lines.append("\nNo common prompts found")
            
        # OpenAPI specs summary
        if context_data["openapi_specs"]:
            summary_lines.append(f"\nOpenAPI Specifications: {len(context_data['openapi_specs'])} files")
            for spec_name in context_data["openapi_specs"].keys():
                summary_lines.append(f"  - {spec_name}")
        else:
            summary_lines.append("\nNo OpenAPI specs found")
            
        return "\n".join(summary_lines)
        
    def validate_lending_structure(self) -> Dict[str, Any]:
        """
        Validate the Lending directory structure and report issues.
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "issues": [],
            "recommendations": [],
            "structure_analysis": {}
        }
        
        try:
            # Check if main directory exists
            if not self.lending_dir.exists():
                validation_result["valid"] = False
                validation_result["issues"].append(f"Lending directory not found: {self.lending_dir}")
                return validation_result
                
            # Check for CommonPrompts directory
            common_prompts_dir = self.lending_dir / "CommonPrompts"
            if not common_prompts_dir.exists():
                validation_result["issues"].append("CommonPrompts directory not found")
                validation_result["recommendations"].append("Create CommonPrompts directory for shared guidelines")
            else:
                txt_files = list(common_prompts_dir.glob("*.txt"))
                validation_result["structure_analysis"]["common_prompts"] = len(txt_files)
                if not txt_files:
                    validation_result["recommendations"].append("Add .txt files to CommonPrompts directory")
                    
            # Check for Capabilities directory
            capabilities_dir = self.lending_dir / "Capabilities"
            if not capabilities_dir.exists():
                validation_result["issues"].append("Capabilities directory not found")
                validation_result["recommendations"].append("Create Capabilities directory for capability-specific content")
            else:
                capabilities = []
                for cap_dir in capabilities_dir.iterdir():
                    if cap_dir.is_dir():
                        cap_analysis = self._analyze_capability_structure(cap_dir)
                        capabilities.append({
                            "name": cap_dir.name,
                            "analysis": cap_analysis
                        })
                        
                validation_result["structure_analysis"]["capabilities"] = capabilities
                
            # Check for root-level OpenAPI specs
            root_specs = list(self.lending_dir.glob("*.yaml")) + list(self.lending_dir.glob("*.yml"))
            openapi_specs = [f for f in root_specs if "openapi" in f.name.lower() or "swagger" in f.name.lower()]
            validation_result["structure_analysis"]["root_openapi_specs"] = len(openapi_specs)
            
            if not validation_result["issues"]:
                validation_result["valid"] = True
                
        except Exception as e:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
            
        return validation_result
        
    def _analyze_capability_structure(self, cap_dir: Path) -> Dict[str, Any]:
        """Analyze the structure of a single capability directory"""
        analysis = {
            "has_original_prompt": False,
            "has_mock_prompt": False,
            "has_original_code": False,
            "has_mock_code": False,
            "original_prompts": 0,
            "mock_prompts": 0,
            "original_specs": 0,
            "mock_specs": 0
        }
        
        # Check prompt directories
        original_prompt_dir = cap_dir / "original-prompt"
        if original_prompt_dir.exists():
            analysis["has_original_prompt"] = True
            analysis["original_prompts"] = len(list(original_prompt_dir.glob("*.txt")))
            
        mock_prompt_dir = cap_dir / "mock-prompt"
        if mock_prompt_dir.exists():
            analysis["has_mock_prompt"] = True
            analysis["mock_prompts"] = len(list(mock_prompt_dir.glob("*.txt")))
            
        # Check code directories
        original_code_dir = cap_dir / "original-code"
        if original_code_dir.exists():
            analysis["has_original_code"] = True
            swagger_dir = original_code_dir / "swagger"
            if swagger_dir.exists():
                analysis["original_specs"] = len(list(swagger_dir.glob("*.yaml")) + list(swagger_dir.glob("*.yml")))
                
        mock_code_dir = cap_dir / "mock-code"
        if mock_code_dir.exists():
            analysis["has_mock_code"] = True
            swagger_dir = mock_code_dir / "swagger"
            if swagger_dir.exists():
                analysis["mock_specs"] = len(list(swagger_dir.glob("*.yaml")) + list(swagger_dir.glob("*.yml")))
                
        return analysis
        
    def get_capability_details(self, capability_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific capability.
        
        Args:
            capability_name: Name of the capability to analyze
            
        Returns:
            Dictionary with detailed capability information
        """
        capabilities = self._extract_capabilities()
        
        if capability_name.lower() not in capabilities:
            return {
                "found": False,
                "error": f"Capability '{capability_name}' not found"
            }
            
        cap_data = capabilities[capability_name.lower()]
        
        return {
            "found": True,
            "name": capability_name,
            "prompts": cap_data.get("prompts", {}),
            "specs": cap_data.get("specs", {}),
            "prompt_count": len(cap_data.get("prompts", {})),
            "spec_count": len(cap_data.get("specs", {})),
            "prompt_types": list(cap_data.get("prompts", {}).keys()),
            "spec_types": list(cap_data.get("specs", {}).keys())
        }