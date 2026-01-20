
import os
import logging
from datetime import datetime
import anthropic
from openai import OpenAI
from backend.config.settings import settings

class TransformationAgent:
    def __init__(self, target_platform='open_liberty'):
        self.target_platform = target_platform
        self.output_dir = settings.OUTPUT_DIR / f'migrated_{target_platform}'
        self.output_dir = str(self.output_dir) # Convert to string for path operations
        
        self.setup_logging()
        
        # Initialize clients
        self.claude_client = None
        if settings.ANTHROPIC_API_KEY:
            self.claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
        self.openai_client = None
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
        self.logger.info(f'Transformation Agent initialized for {target_platform}')

    def setup_logging(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = settings.LOG_DIR / f'transformation_agent_{timestamp}.log'
        
        self.logger = logging.getLogger('TransformationAgent')
        self.logger.setLevel(logging.INFO)
        
        # Avoid adding multiple handlers if already configured
        if not self.logger.handlers:
            fh = logging.FileHandler(str(log_file))
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(fh)
            
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter('%(message)s')) # Simpler console output
            self.logger.addHandler(ch)
            
        self.log_file = str(log_file)

    def call_llm(self, prompt, provider="claude"):
        """Unified method to call LLMs"""
        try:
            if provider == "claude" and self.claude_client:
                self.logger.info('Calling Claude API (claude-sonnet-4-5)')
                self.logger.info("DEBUG: Starting Claude API call...")
                try:
                    response = self.claude_client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=4000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    self.logger.info(f"DEBUG: Claude API returned: {type(response)}")
                    return response.content[0].text.strip()
                except Exception as e:
                    import traceback
                    self.logger.error(f"DEBUG: Claude API Error: {e}")
                    self.logger.error(traceback.format_exc())
                    raise e
            
            elif provider == "openai" and self.openai_client:
                self.logger.info('Calling OpenAI API')
                self.logger.info("DEBUG: Starting OpenAI API call...")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,
                    temperature=0.1
                )
                self.logger.info("DEBUG: OpenAI API returned result")
                return response.choices[0].message.content.strip()
            
            else:
                 msg = f"Provider {provider} not available or configured (Key present: {bool(self.claude_client)})"
                 self.logger.error(msg)
                 return None
                 
        except Exception as e:
            self.logger.error(f"LLM API error ({provider}): {e}")
            self.logger.error(f"DEBUG: General LLM Error: {e}")
            return None

    def transform_code(self, source_path, filename, llm_provider="claude", validation_feedback=None):
        """Transform a single file with optional feedback"""
        self.logger.info(f"Transforming {filename} using {llm_provider}")
        
        try:
            with open(source_path, 'r') as f:
                source_code = f.read()
        except Exception as e:
            return {'status': 'failed', 'error': f"Read error: {e}"}

        # Select Prompt
        if validation_feedback:
            prompt = self._create_feedback_prompt(source_code, filename, validation_feedback)
        elif filename.endswith('.xml'):
            prompt = self._create_xml_prompt(source_code, filename)
        else:
             prompt = self._create_java_prompt(source_code, filename)
             
        # Call LLM
        result = self.call_llm(prompt, llm_provider)
        
        if result:
            # simple cleanup
            cleaned = result.replace("```java", "").replace("```xml", "").replace("```", "").strip()
            return {'status': 'success', 'transformed_code': cleaned}
        else:
            return {'status': 'failed', 'error': "No response from LLM"}

    def migrate_application(self, source_files, llm_provider="claude", validation_feedback=None):
        """Main entry point for migration"""
        self.logger.info("Starting migration...")
        self._create_dir_structure()
        
        results = {
            'target_platform': self.target_platform,
            'output_dir': self.output_dir,
            'files_transformed': {},
            'new_files': []
        }
        
        # 1. Transform Source Files
        for filename, filepath in source_files.items():
            self.logger.info(f"Processing {filename}")
            res = self.transform_code(filepath, filename, llm_provider, validation_feedback)
            
            if res['status'] == 'success':
                # Determine output path based on type
                if filename.endswith('.java'):
                    out_path = os.path.join(self.output_dir, 'src/main/java/com/company/customer', filename)
                elif filename == 'server.xml':
                    out_path = os.path.join(self.output_dir, 'src/main/liberty/config', filename)
                elif filename in ['web.xml', 'ejb-jar.xml']:
                    out_path = os.path.join(self.output_dir, 'src/main/webapp/WEB-INF', filename)
                elif filename == 'persistence.xml':
                    out_path = os.path.join(self.output_dir, 'src/main/resources/META-INF', filename)
                else: 
                     # Default fallback
                     out_path = os.path.join(self.output_dir, 'src/main/resources', filename)

                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'w') as f:
                    f.write(res['transformed_code'])
                results['new_files'].append(out_path)
            
            results['files_transformed'][filename] = res

        # 2. Generate POM if not present/transformed (usually generated fresh)
        pom_content = self.generate_pom(llm_provider)
        if pom_content:
            pom_path = os.path.join(self.output_dir, 'pom.xml')
            with open(pom_path, 'w') as f:
                f.write(pom_content)
            results['new_files'].append(pom_path)
        
        # 3. Generate server.xml for Open Liberty
        server_xml_content = self._generate_server_xml()
        if server_xml_content:
            server_xml_path = os.path.join(self.output_dir, 'src/main/liberty/config/server.xml')
            os.makedirs(os.path.dirname(server_xml_path), exist_ok=True)
            with open(server_xml_path, 'w') as f:
                f.write(server_xml_content)
            results['new_files'].append(server_xml_path)
            
        return results

    def generate_pom(self, llm_provider=None):
        """Generate a deterministic Maven pom.xml for Open Liberty with Java EE 8 (javax.*)
        
        CRITICAL: Uses Java EE 8 dependencies (javax.* namespace) NOT Jakarta EE 9+ (jakarta.*)
        This ensures compatibility with transformed WebSphere code that uses javax.servlet imports.
        """
        return """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.company</groupId>
    <artifactId>customer-portal-liberty</artifactId>
    <version>1.0.0</version>
    <packaging>war</packaging>
    <name>Customer Portal - Open Liberty</name>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <failOnMissingWebXml>false</failOnMissingWebXml>
    </properties>
    
    <dependencies>
        <!-- Java EE 8 Web Profile (javax.* namespace) - NOT Jakarta! -->
        <dependency>
            <groupId>javax.servlet</groupId>
            <artifactId>javax.servlet-api</artifactId>
            <version>4.0.1</version>
            <scope>provided</scope>
        </dependency>
        
        <dependency>
            <groupId>javax.enterprise</groupId>
            <artifactId>cdi-api</artifactId>
            <version>2.0</version>
            <scope>provided</scope>
        </dependency>
        
        <dependency>
            <groupId>javax.ws.rs</groupId>
            <artifactId>javax.ws.rs-api</artifactId>
            <version>2.1.1</version>
            <scope>provided</scope>
        </dependency>
        
        <dependency>
            <groupId>javax.json</groupId>
            <artifactId>javax.json-api</artifactId>
            <version>1.1.4</version>
            <scope>provided</scope>
        </dependency>
        
        <dependency>
            <groupId>javax.annotation</groupId>
            <artifactId>javax.annotation-api</artifactId>
            <version>1.3.2</version>
            <scope>provided</scope>
        </dependency>
        
        <!-- Jakarta Persistence API (still uses javax.persistence) -->
        <dependency>
            <groupId>javax.persistence</groupId>
            <artifactId>javax.persistence-api</artifactId>
            <version>2.2</version>
            <scope>provided</scope>
        </dependency>
        
        <!-- Testing -->
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.9.3</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <finalName>customer-portal-liberty</finalName>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>
            
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-war-plugin</artifactId>
                <version>3.3.2</version>
                <configuration>
                    <failOnMissingWebXml>false</failOnMissingWebXml>
                </configuration>
            </plugin>
            
            <plugin>
                <groupId>io.openliberty.tools</groupId>
                <artifactId>liberty-maven-plugin</artifactId>
                <version>3.8.2</version>
                <configuration>
                    <serverName>defaultServer</serverName>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""

    def _create_dir_structure(self):
        dirs = [
            'src/main/java/com/company/customer',
            'src/main/resources/META-INF',
            'src/main/webapp/WEB-INF',
            'src/main/liberty/config',
            'src/test/java'
        ]
        for d in dirs:
            os.makedirs(os.path.join(self.output_dir, d), exist_ok=True)

    def _generate_server_xml(self):
        """Generate Open Liberty server.xml configuration"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<server description="Open Liberty Server">
    <featureManager>
        <feature>jakartaee-8.0</feature>
        <feature>microProfile-4.1</feature>
    </featureManager>
    
    <httpEndpoint id="defaultHttpEndpoint"
                  host="*"
                  httpPort="9080"
                  httpsPort="9443" />
    
    <webApplication location="customer-portal-liberty.war" contextRoot="/" />
    
    <applicationManager autoExpand="true"/>
</server>
"""

    def _create_java_prompt(self, source, filename):
        return f"""You are an expert Java developer specializing in WebSphere to Open Liberty migration.

TASK: Transform the following WebSphere code to Open Liberty with Jakarta EE 8 compatibility:

1. COMPLETE TRANSFORMATION:
   - Convert ALL @EJB annotations to @Inject (CDI)
   - Replace @Stateless with @ApplicationScoped  
   - Convert WebSphere Security APIs to MicroProfile JWT
   - Update JMS code for Liberty compatibility
   - Fix all imports and package declarations

2. JAKARTA EE 8 COMPATIBILITY:
   - Use javax.* imports (NOT jakarta.*) for Jakarta EE 8
   - Ensure all annotations use javax.* packages
   - Use proper CDI and MicroProfile imports

3. CODE CORRECTNESS:
   - Ensure proper Java syntax (package declaration FIRST, then imports)
   - Remove ALL WebSphere-specific imports (com.ibm.websphere.*)
   - Maintain method signatures and business logic
   - Fix any syntax errors or malformed code

   - Return ONLY the complete, valid Java/XML code
   - No explanations, comments, or markdown formatting
   - Ensure code compiles without errors
   - Maintain all original business logic

   CRITICAL IMPORT RULES:
   - YOU MUST USE 'javax.*' PACKAGES (e.g., javax.ejb, javax.inject, javax.persistence)
   - DO NOT USE 'jakarta.*' PACKAGES. This project is strictly Jakarta EE 8 (javax namespace).
   - If you use 'jakarta.*', the code will fail to compile.


FILENAME: {filename}
SOURCE CODE:
{source}"""

    def _create_xml_prompt(self, source, filename):
        return f"""Transform this WebSphere XML to Open Liberty format:

FILENAME: {filename}
SOURCE XML:
{source}

Return ONLY the transformed XML, no explanations."""

    def _create_feedback_prompt(self, source, filename, feedback):
        # Simplified feedback prompt construction
        errors = "Unknown errors"
        if isinstance(feedback, dict):
            # Try to extract maven errors
            tests = feedback.get('tests', {})
            mvn = tests.get('maven_build', {})
            errors = mvn.get('error') or mvn.get('stderr') or str(feedback)
            
        return f"""You are an expert Java developer fixing WebSphere to Open Liberty migration issues.

CRITICAL: The previous transformation had COMPILATION ERRORS. You must fix these specific issues:

ERRORS:
{str(errors)[:2000]}

TRANSFORMATION TASK:
Transform this WebSphere code to Open Liberty, addressing ALL the above compilation errors:

FILENAME: {filename}
SOURCE CODE:
{source}

OUTPUT REQUIREMENTS:
- Return ONLY the complete, compilable Java/XML code
- No explanations or markdown formatting
- Address ALL compilation errors mentioned above
- Ensure consistency between imports and target Jakarta EE version"""
