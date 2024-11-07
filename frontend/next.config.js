/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack(config) {
    config.module.rules.push({
      test: /\.svg$/,
      include: /assets/,
      use: [
        {
          loader: 'file-loader',
          options: {
            name: '[name].[hash].[ext]',
            outputPath: 'static/assets/',
            publicPath: '/_next/static/assets/',
          },
        },
      ],
    });

    return config;
  },
};

module.exports = nextConfig;
