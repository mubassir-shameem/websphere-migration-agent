# Transformation Agent Logic

Located in: `backend/app/agents/transformation.py`

## Core Responsibilities
1.  **Iterate Source Code**: Scans the input directory for `.java` and `*.xml` files.
2.  **LLM Transformation**: Sends each file to the LLM (Claude-Sonnet) with a specialized prompt to rewrite WebSphere APIs (e.g., `javax.ejb`, `CommonJ`) to Jakarta EE/MicroProfile.
3.  **Config Generation**:
    - Converts `web.xml` and `ejb-jar.xml` concepts into `server.xml` (Open Liberty configuration).
    - Generates a `pom.xml` with the correct Jakarta EE 8 dependencies.
4.  **Package Structure**:
    - Dynamically detects the source package structure (looking for `src/main/java`).
    - Replicates this structure in the output directory to ensure the generated Java files have the correct directory path matching their `package` declaration.

## Logic Flow
```python
def migrate_application(source_files):
    create_dir_structure()
    
    for file in source_files:
        # LLM Call (Async in Threadpool)
        transformed_code = transform_code(file)
        
        # Save to Output
        path = determine_output_path(file) # Uses src/main/java detection
        write_file(path, transformed_code)
        
    generate_pom()
    generate_server_xml()
```

## Smart Iteration (Cost Optimization)
The agent defaults to `max_iterations=1`.
- **Iteration 1**: Transforms all files.
- **Future**: If `max_iterations > 1` and Validation fails, it will only re-process files mentioned in the compiler error logs (Smart Repair).
