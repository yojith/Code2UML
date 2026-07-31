export type LanguageId = "python" | "java" | "cpp" | "c";

export const LANGUAGES: readonly {
  id: LanguageId;
  label: string;
  extensions: readonly string[];
  commandId: string;
}[] = [
  {
    id: "python",
    label: "Python",
    extensions: ["py"],
    commandId: "code2uml.generatePython",
  },
  {
    id: "java",
    label: "Java",
    extensions: ["java"],
    commandId: "code2uml.generateJava",
  },
  {
    id: "cpp",
    label: "C++",
    extensions: ["cpp", "cc", "cxx", "hpp", "hh", "h"],
    commandId: "code2uml.generateCpp",
  },
  {
    id: "c",
    label: "C",
    extensions: ["c", "h"],
    commandId: "code2uml.generateC",
  },
];
