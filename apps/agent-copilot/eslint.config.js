import react from 'eslint-plugin-react';

export default [
  {
    files: ['**/*.js', '**/*.jsx'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: { react },
    rules: {
      'react/jsx-uses-react': 'warn',
      'react/jsx-uses-vars': 'warn',
    },
  },
];
