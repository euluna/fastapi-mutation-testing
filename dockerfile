FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /work

# Install only the tools you need
RUN pip install --no-cache-dir mutmut pytest fastapi[all] httpx

# Keep the container alive so you can exec into it
CMD ["tail", "-f", "/dev/null"]