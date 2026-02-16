import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useCallback, useTransition } from "react";

export interface UrlFilterParams {
  page?: string;
  search?: string;
  company?: string;
  location?: string;
  category?: string;
  visa_sponsored?: string;
  f1_friendly?: string;
  job_type?: string;
  work_mode?: string;
  posted_within?: string;
  matched?: string;
  selected?: string;
}

export function useUrlFilters() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const params: UrlFilterParams = {
    page: searchParams.get("page") || undefined,
    search: searchParams.get("search") || undefined,
    company: searchParams.get("company") || undefined,
    location: searchParams.get("location") || undefined,
    category: searchParams.get("category") || undefined,
    visa_sponsored: searchParams.get("visa_sponsored") || undefined,
    f1_friendly: searchParams.get("f1_friendly") || undefined,
    job_type: searchParams.get("job_type") || undefined,
    work_mode: searchParams.get("work_mode") || undefined,
    posted_within: searchParams.get("posted_within") || undefined,
    matched: searchParams.get("matched") || undefined,
    selected: searchParams.get("selected") || undefined,
  };

  const currentPage = parseInt(params.page || "1", 10);

  const updateFilter = useCallback((key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams.toString());
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    newParams.delete("page");
    startTransition(() => {
      router.push(`${pathname}?${newParams.toString()}`);
    });
  }, [searchParams, router, pathname]);

  const updateMultiSelect = useCallback((key: string, values: string[]) => {
    updateFilter(key, values.join("|"));
  }, [updateFilter]);

  const clearFilters = useCallback(() => {
    startTransition(() => {
      router.push(pathname);
    });
  }, [router, pathname]);

  const getMultiSelectValue = useCallback((key: string): string[] => {
    return searchParams.get(key)?.split("|").filter(Boolean) || [];
  }, [searchParams]);

  const buildPageUrl = useCallback((page: number): string => {
    const newParams = new URLSearchParams(searchParams.toString());
    newParams.set("page", page.toString());
    newParams.delete("selected");
    return `${pathname}?${newParams.toString()}`;
  }, [searchParams, pathname]);

  return {
    searchParams,
    params,
    currentPage,
    isPending,
    updateFilter,
    updateMultiSelect,
    clearFilters,
    getMultiSelectValue,
    buildPageUrl,
  };
}
