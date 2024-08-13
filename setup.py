import setuptools

requirements = ['selenium==4.1.0',
                'webdriver-manager==3.2.2',
                'selenium-wire==5.1.0',
                'python-dateutil==2.8.2',
                'python-dotenv==1.0.1',
                'aiohttp==3.10.3']

setuptools.setup(
    name="scraper",
    version="0.0.1",
    license="MIT",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP"

    ],
    python_requires=">=3.7",
    install_requires=requirements
)
