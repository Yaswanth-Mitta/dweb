# Use Nginx to serve a static React app
FROM nginx:alpine

# Copy static files to Nginx html directory
COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]