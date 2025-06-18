from setuptools import setup, find_packages

setup(
    name='query_tables',
    version='1.0.0',
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
    url='https://github.com/AntonGlyzin/query_tables',
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
    ]
)