import { AirQuality } from "./components/AirQuality";
import { Evidence } from "./components/Evidence";
import { Explorer } from "./components/Explorer";
import { Footer } from "./components/Footer";
import { Hero } from "./components/Hero";
import { Methodology } from "./components/Methodology";
import { Nav } from "./components/Nav";
import { Resources } from "./components/Resources";
import { Summary } from "./components/Summary";

export default function App() {
  return (
    <>
      <a href="#summary" className="sr-only z-[200] rounded bg-white px-3 py-2 focus:not-sr-only focus:fixed focus:left-3 focus:top-3">
        Skip to content
      </a>
      <Nav />
      <main>
        <Hero />
        <Summary />
        <Explorer />
        <AirQuality />
        <Evidence />
        <Methodology />
        <Resources />
      </main>
      <Footer />
    </>
  );
}
