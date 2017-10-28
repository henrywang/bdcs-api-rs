#pylint: disable=missing-docstring,import-error,too-many-public-methods

import os
import unittest
from subprocess import check_output, CalledProcessError

import toml

try:
    from parameterized import parameterized
except ImportError:
    # on Fedora 25 (Docker)
    from nose_parameterized import parameterized


_TEST_DIR = os.path.dirname(__file__)

_RECIPE_DIR = os.path.join(_TEST_DIR, '..', '..', 'examples', 'recipes')
_RECIPE_DIR = os.path.abspath(_RECIPE_DIR)

_KCOV = []
if os.environ.get('KCOV'):
    _KCOV = [
        os.environ['KCOV'],
        '--include-path=%s' % os.path.abspath(os.path.join(_TEST_DIR, '..', '..', 'src')),
        os.path.abspath(os.path.join(_TEST_DIR, '..', '..', 'target', 'kcov')),
    ]

_DEPCLOSE = os.path.join(_TEST_DIR, '..', '..', 'target', 'debug', 'depclose')
_DEPCLOSE = _KCOV + [
    os.path.abspath(_DEPCLOSE),
    os.environ.get('METADATA_DB', 'metadata.db')
]

_RECIPES = []
for _dirpath, _dirnames, filenames in os.walk(_RECIPE_DIR):
    for _recipe in filenames:
        if _recipe.endswith('.toml'):
            _RECIPES.append(_recipe)


def read_toml(fname):
    return toml.loads(open(os.path.join(_RECIPE_DIR, fname), 'r').read())

def exec_depclose(package_list):
    # will raise CalledProcessError exception if depclose
    # exit status is != 0
    return check_output(_DEPCLOSE + package_list)


class DepcloseTestCase(unittest.TestCase):
    @parameterized.expand(_RECIPES)
    def test_depclose(self, recipe_file):
        recipe = read_toml(recipe_file)

        packages = []
        for key in ['packages', 'modules']:
            if key in recipe:
                for pkg in recipe[key]:
                    packages.append(pkg['name'])

        # step 1: can we resolve all the dependencies
        try:
            recipe_name = recipe_file.replace('.toml', '')
            depclose_output = exec_depclose(packages)
        except CalledProcessError as err:
            # KNOWN ISSUE, WONT FIX, SKIP
            # https://trello.com/c/0D3pbzaA/291-bug-depclose-is-killed-when-mddb-contains-updates
            if recipe_name in ['kubernetes', 'jboss']:
                self.skipTest('known issue for %s' % recipe_name)

            self.assertEqual('', err.output)
            self.fail('depclose failed!')

        # step 2: is what the user wanted still in the list
        for pkg in packages:
            self.assertIn(pkg, depclose_output)

        # step 3: sanity test specific functionality
        # iow if user wanted http server, make sure there is one
        # and it can actually serve files!
        # build the recipe and produce a Docker image
        # then spin this image up and use https://github.com/docker/golem
        # to run functional tests on it

if __name__ == "__main__":
    unittest.main()
