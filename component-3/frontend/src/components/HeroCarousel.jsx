import React, { useEffect, useState } from "react";

const SLIDES = [
  { src: "/hero/waste_01.jpeg", alt: "Overflowing recycling bin with sorted plastic and glass" },
  { src: "/hero/waste_02.jpeg", alt: "Color-coded bins for paper, glass, plastic, e-waste, metal and organic waste" },
  { src: "/hero/waste_03.jpeg", alt: "Person sorting a cup into the correct recycling bin" },
];

export default function HeroCarousel({ intervalMs = 4000 }) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setActive(i => (i + 1) % SLIDES.length), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return (
    <div className="hero-carousel">
      {SLIDES.map((slide, i) => (
        <img
          key={slide.src}
          src={slide.src}
          alt={slide.alt}
          className={`hero-carousel-slide${i === active ? " active" : ""}`}
        />
      ))}
      <div className="hero-carousel-dots">
        {SLIDES.map((slide, i) => (
          <button
            key={slide.src}
            type="button"
            className={`hero-carousel-dot${i === active ? " active" : ""}`}
            aria-label={`Show slide ${i + 1}`}
            onClick={() => setActive(i)}
          />
        ))}
      </div>
    </div>
  );
}
