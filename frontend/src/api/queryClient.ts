import { QueryClient } from "@tanstack/react-query";
import { deveTentarDeNovo } from "./chamar";

export function criarQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: deveTentarDeNovo } } });
}
