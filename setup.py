import os
from setuptools import setup, find_packages

# Для изменения версии программы 
# сообщение коммита должно содержать: "feat:" / "fix:".
VERSION_APP = os.getenv('VERSION_APP')

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='query_tables',
    version=VERSION_APP,
    package_data={"": ["LICENSE", ]},
    packages=find_packages(),
    install_requires=[
        'cachetools<=6.0.0',
        'aiosqlite<=0.21.0',
        'psycopg2<=2.9.10',
        'asyncpg<=0.30.0',
        'redis<=6.2.0'
    ],
    python_requires=">=3.9",
    author='Антон Глызин',
    author_email='tosha.glyzin@mail.ru',
    description='Запросы в объектном стиле без моделей с поддержкой кеша данных.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='MIT',
    keywords='asyncio orm sql postgres sqlite cache redis python',
    classifiers=[
        'Intended Audience :: Developers',
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries",
    ],
    project_urls={
        "Releases": "https://github.com/AntonGlyzin/query_tables/releases",
        "Github": "https://github.com/AntonGlyzin/query_tables"
    },
)