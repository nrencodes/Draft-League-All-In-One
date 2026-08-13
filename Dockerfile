# Import specified version of Python supported
FROM python:3.13

# Change to working directory and install requirements
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy remaining files into working directory
COPY . . 

# Run the program
CMD ["python3", "-u", "Bot.py"]

