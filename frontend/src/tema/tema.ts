import { createTheme } from "@mantine/core";
import { tokens } from "./tokens";

export const tema = createTheme({
  primaryColor: tokens.corPrimaria,
  fontFamily: tokens.fonte,
  defaultRadius: tokens.raio,
});
