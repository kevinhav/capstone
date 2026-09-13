# Instructions

## Project Structure

- uv is the package manager and project manager. Use it to install packages and run scripts and modules in this project
- Use a src/project layout, installed in editable mode using `uv pip install -e .`
- Imports should be absolute, such as `core.data` instead of `.data`
- Documents generated for the project should live in `/docs`, while reference materials from other sources live in `/references`
- Data is stored in `/data` and further subdivided into `data/raw`, `data/interim`, and `data/processed`. Raw data is immutable, interim data is for temporary results that we've touched but are not yet finalized (usually to save heavy computation steps), and processed should be a final output.

## Code Style

- Code should be functional unless there is clear benefit from building custom classes
- Functions should be single responsibility and modular. Helper functions can be denoted with a `_` prefix
- Only build CLI arguments if specifically requested.
- All code should be fully typed. If there is benefit in defining a custom type, it should be done across the project and reused.
- Do not write excessive boilerplate to cover each and every edge case; use the type system and data contracts at interface points
- Use loguru for logging instead of print statements. Store logs in /logs and use them to debug. Use appropriate classifications such as DEBUG, INFO, WARNING, etc.
- Use dataclasses to contain config parameters or other collections of internal data
- Use pandas for all common tabular data manipulation tasks, including I/O. 
- If building a pandas data pipeline, use `pipe()` to orchestrate each step instead of reassigning a dataframe to each function call
- Avoid "magic strings" by using constants or Enums to define things like canonical column names, constants, or by abstracting the string to a function args 
- Project Paths should be managed from a single ProjectPath dataclass using Pathlib. 
- Public functions should have full docstrings.
  

## Version Control

- Branch strategy by default uses `main`, `dev`, `feature/my_feature`, and `exp/test_new_library` as usually branches. Main merges from dev, dev merges from feature and experiments. Features are new code key to the functionality of the project, while experimental branches are for testing things and generally considered throwaway
- We will use `git restore` liberally if code is not acceptable quality or the implementation is not correct
- Large changes should always be done on a fresh branch. Use git stash if the current working state is not committes
- Medium changes should always be done on a fresh commit. Ask the user to confirm committing or stashing current changes before making further edits
- Small changes do not need an explicit version control process
- Do not commit or version control data files.