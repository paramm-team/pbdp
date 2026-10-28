import nox


@nox.session
def lint(session):
    """Run the flake8 linter."""
    session.install('flake8')
    session.run('flake8', './pbdp/', './tests/', './tools/',
                './examples/scripts/quickstart.py')


@nox.session
def sphinx(session):
    """Build the documentation."""
    session.install('-e', './[docs]')
    session.run('sphinx-build', '-b', 'html', 'docs', 'docs/_build/html', '-W')


@nox.session(python=['3.8', '3.9', '3.10', '3.11', '3.12'])
def integration(session):
    """Run the integration test suite."""
    session.install('-e', './[dev]')

    # Get the files to test
    if session.posargs:
        test_files = session.posargs
    else:
        test_files = ["./tests/integration/"]

    session.run("pytest", *test_files)


@nox.session(python=['3.8', '3.9', '3.10', '3.11', '3.12'])
def unit(session):
    """Run the unit test suite."""
    session.install('-e', './[dev]')

    # Get the files to test
    if session.posargs:
        test_files = session.posargs
    else:
        test_files = ["./tests/unit/"]

    session.run("pytest", *test_files)


@nox.session()
def coverage(session):
    """Run the unit test suite with coverage."""
    session.install('-e', './[dev]')

    session.run("coverage", "run", "--source=./pbdp", "-m",
                "pytest", "./tests/")
    session.run("coverage", "report", "-m")
    session.run("coverage", "xml")
