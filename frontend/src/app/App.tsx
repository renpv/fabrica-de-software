import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { tema } from "../tema/tema";
import { RotasApp } from "./rotas";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={tema}>
        <BrowserRouter>
          <RotasApp />
        </BrowserRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
}
