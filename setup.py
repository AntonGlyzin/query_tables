import os
from setuptools import setup, find_packages

fix = int(os.getenv('COUNT_COMMITS_FIX'))
feat = int(os.getenv('COUNT_COMMITS_FEAT'))

setup(
    name='query_tables',
    version=f'1.{feat}.{fix}',
    package_data={"": ["LICENSE", ]},
    packages=find_packages(),
    install_requires=[
        'cachetools<=6.0.0',
        'aiosqlite<=0.21.0',
        'psycopg2<=2.9.10',
        'asyncpg<=0.30.0'
    ],
    python_requires=">=3.9",
    author='Антон Глызин',
    author_email='tosha.glyzin@mail.ru',
    url='https://pypi.org/project/query-tables',
    description='Запросы в объектном стиле без моделей с поддержкой кеша данных.',
    long_description=open('README.md', encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    license='MIT License',
    keywords='orm sql postgres sqlite cache python',
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
        "Documentation": "https://pypi.org/project/query-tables",
        "Source": "https://github.com/AntonGlyzin/query_tables",
    },
)