/* SPDX-License-Identifier: AGPL-3.0-or-later
* Copyright (C) 2025-2026 Aidan Murphy
*/

// these must be listed in the pre-commit config .yaml under additional_dependencies
const globals = require('globals');
const js = require('@eslint/js');
const stylistic = require('@stylistic/eslint-plugin');
const jsdoc = require('eslint-plugin-jsdoc');

module.exports = [
  jsdoc.configs['flat/recommended'],
  { ignores: [
    // ignore vendored files
    'plom_server/plom_extra_static/js3rdparty/**',
    // This file isn't from Plom
    'plom_server/static/js/bootstrap_lightdark_mode.js',
  ] },
  {
    files: ['**/*.js', '**/*.cjs', '**/*.jsx', '**/*.ts', '**/*.tsx'],

    plugins: { '@stylistic': stylistic, 'jsdoc': jsdoc },
    // Source - https://stackoverflow.com/questions/59644872/how-to-specify-my-environment-in-eslint
    // Posted by papillon
    // Retrieved 2025-11-19, License - CC BY-SA 4.0
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },

    // full list of eslint rules here: https://eslint.org/docs/latest/rules/
    rules: {
      ...js.configs.recommended.rules,
      ...stylistic.configs.recommended.rules,

      // jsdoc rules here: https://github.com/gajus/eslint-plugin-jsdoc/tree/HEAD/docs/rules
      'jsdoc/require-jsdoc': ['error', {
        require: {
          FunctionDeclaration: true,
          FunctionExpression: true,
          MethodDefinition: true,
        },
      }],
      'jsdoc/require-description': 'error',
      'jsdoc/require-description-complete-sentence': 'error',
      'jsdoc/require-hyphen-before-param-description': ['error', 'always'],
      // 'jsdoc/require-params': 'off',

      'no-console': 'error',
      '@stylistic/semi': ['error', 'always'],
    },
  },
];
