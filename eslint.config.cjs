/* SPDX-License-Identifier: AGPL-3.0-or-later
* Copyright (C) 2025 Aidan Murphy
*/

// these must be listed in the pre-commit config .yaml under additional_dependencies
const globals = require("globals");
const js = require("@eslint/js");
const stylistic = require("@stylistic/eslint-plugin");

module.exports = [
    {
        files: ["**/*.js", "**/*.cjs", "**/*.jsx", "**/*.ts", "**/*.tsx"],

        plugins: { "@stylistic": stylistic },
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
            "no-console": "error",
            "@stylistic/indent": ["error", 4],
            "@stylistic/quotes": ["error", "double"],
            "@stylistic/semi": ["error", "always"],
        },
    },
];
