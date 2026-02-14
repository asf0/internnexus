import { MetadataRoute } from "next";
import { fetchJobs } from "../lib/api";
import { BASE_URL } from "../lib/config";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const data = await fetchJobs({ page_size: 1000 });
  
  const jobUrls: MetadataRoute.Sitemap = data.items.map((job) => ({
    url: `${BASE_URL}/jobs/${job.id}`,
    lastModified: job.posted_at ? new Date(job.posted_at) : new Date(),
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  return [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    ...jobUrls,
  ];
}
