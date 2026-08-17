import "@testing-library/jest-dom/vitest";

(window as unknown as { scrollTo: () => void }).scrollTo = () => {};