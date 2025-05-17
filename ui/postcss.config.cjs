// postcss.config.cjs for ES module compatibility and new Tailwind plugin
module.exports = {
  plugins: [
    require('@tailwindcss/postcss'),
    require('autoprefixer'),
  ],
}; 