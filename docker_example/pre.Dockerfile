FROM cloudgeometry/langbuilder:1.0-alpha

CMD ["python", "-m", "langbuilder", "run", "--host", "0.0.0.0", "--port", "7860"]
