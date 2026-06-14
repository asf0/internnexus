import { GlobalRegistrator } from "@happy-dom/global-registrator";
import "@testing-library/jest-dom/vitest";

// Register Happy DOM for React Testing Library
GlobalRegistrator.register();
