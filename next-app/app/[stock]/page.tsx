"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

export default function StockPage() {
  const { stock } = useParams(); // Get the stock symbol from the URL
  const [predictedPrice, setPredictedPrice] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPrediction = async () => {
      try {
        const response = await fetch(`http://localhost:8000/predict?stock=${stock}`);
        const data = await response.json();
        if (response.ok) {
          setPredictedPrice(data.predicted_price);
          setError(null);
        } else {
          setError(data.error || "Failed to fetch prediction");
        }
      } catch (err) {
        setError("Error fetching prediction");
        console.error(err);
      }
    };

    fetchPrediction();
  }, [stock]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-100">
      <h1 className="text-4xl font-bold text-center mb-8">{stock} Stock Prediction</h1>
      {error ? (
        <p className="text-red-500">{error}</p>
      ) : predictedPrice !== null ? (
        <p className="text-2xl font-semibold">Predicted Price: ${predictedPrice.toFixed(2)}</p>
      ) : (
        <p className="text-gray-500">Loading prediction...</p>
      )}
    </div>
  );
}