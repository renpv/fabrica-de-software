import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { RotasApp } from "../app/rotas";
import { tema } from "../tema/tema";

export function renderizarApp(rota: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={tema}>
        <MemoryRouter initialEntries={[rota]}>
          <RotasApp />
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>,
  );
}
