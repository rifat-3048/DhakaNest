import HomeFooter from "@/components/home/HomeFooter";
import HomeSections from "@/components/home/HomeSections";
import HeroSection from "@/components/home/HeroSection";

export default function HomePage() {
  return (
    <>
      <main className="overflow-hidden">
        <HeroSection />
        <HomeSections />
      </main>
      <HomeFooter />
    </>
  );
}
