import setuptools


def main() -> None:
    install_requires = ['selenium',
                        'webdriver-manager',
                        'selenium-wire',
                        'python-dateutil',
                        'python-dotenv',
                        'aiohttp',
                        'pydantic',
                        'blinker',
                        'ruamel.yaml',
                        'appdirs']

    setuptools.setup(
        name="scraper",
        version="0.0.1",
        packages=setuptools.find_packages(),
        url="",
        author="",
        author_email="",
        license="",
        scripts=["bin/main.py"],
        python_requires=">=3.7",
        install_requires=install_requires
    )


if __name__ == "__main__":
    main()
